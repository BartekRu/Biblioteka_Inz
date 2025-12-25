"""
recommendation_engine/service.py
Główny serwis rekomendacji z integracją LightGCN + MMR re-ranking
"""

import os
import pickle
import numpy as np
from typing import List, Dict, Optional
import logging
from pathlib import Path

# Import MMR
from .mmr_reranking import (
    mmr_rerank,
    apply_mmr_with_offset,
    extract_book_embeddings_from_model,
    diversity_metrics,
)

logger = logging.getLogger(__name__)

# Ścieżki do modelu
MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "lightgcn_model.pkl"
MAPPINGS_PATH = MODEL_DIR / "id_mappings.pkl"


class RecommendationService:
    """Serwis rekomendacji z LightGCN + MMR"""

    def __init__(self):
        self.model = None
        self.user_id_map = {}  # MongoDB str -> internal int
        self.book_id_map = {}  # MongoDB str -> internal int
        self.reverse_book_map = {}  # internal int -> MongoDB str
        self.book_embeddings_dict = {}  # book_id_str -> embedding ndarray
        self.model_loaded = False

        self._load_model()

    def _load_model(self):
        """Ładuje wytrenowany model LightGCN"""
        try:
            if not MODEL_PATH.exists():
                logger.warning(f"⚠️ Model nie znaleziony: {MODEL_PATH}")
                return

            # Załaduj model
            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)

            # Załaduj mapowania ID
            if MAPPINGS_PATH.exists():
                with open(MAPPINGS_PATH, "rb") as f:
                    mappings = pickle.load(f)
                    self.user_id_map = mappings.get("user_id_map", {})
                    self.book_id_map = mappings.get("book_id_map", {})
                    self.reverse_book_map = {v: k for k, v in self.book_id_map.items()}

            # Wyciągnij embeddingi książek
            if hasattr(self.model, "book_embeddings"):
                for book_id_str, internal_id in self.book_id_map.items():
                    embedding = self.model.book_embeddings[internal_id].detach().cpu().numpy()
                    self.book_embeddings_dict[book_id_str] = embedding

            self.model_loaded = True
            logger.info(
                f"✅ Model załadowany: {len(self.user_id_map)} użytkowników, "
                f"{len(self.book_id_map)} książek"
            )

        except Exception as e:
            logger.error(f"❌ Błąd ładowania modelu: {e}")
            self.model_loaded = False

    def get_recommendations(
        self,
        user_id: str,
        n: int = 30,
        offset: int = 0,
        use_mmr: bool = True,
        lambda_param: float = 0.7,
        enforce_author_limit: bool = True,
        max_per_author: int = 2,
        exclude_book_ids: Optional[List[str]] = None,
    ) -> Dict:
        """
        Generuje rekomendacje dla użytkownika.

        Args:
            user_id: MongoDB ObjectId użytkownika (jako string)
            n: Liczba rekomendacji do zwrócenia
            offset: Offset dla rotacji (działa tylko z MMR)
            use_mmr: Czy użyć MMR re-ranking
            lambda_param: Parametr MMR (0.0=różnorodność, 1.0=trafność)
            enforce_author_limit: Czy ograniczać książki tego samego autora
            max_per_author: Max książek od jednego autora
            exclude_book_ids: Lista book_id do wykluczenia

        Returns:
            Dict z:
            - recommendations: Lista książek
            - metadata: Informacje o generowaniu (model, MMR, metryki)
        """
        if not self.model_loaded:
            logger.error("❌ Model nie załadowany")
            return {
                "recommendations": [],
                "metadata": {"error": "Model not loaded", "model_available": False},
            }

        # Sprawdź czy użytkownik istnieje w modelu
        if user_id not in self.user_id_map:
            logger.warning(f"⚠️ Użytkownik {user_id[:8]}... nie znaleziony w modelu")
            return {
                "recommendations": [],
                "metadata": {
                    "error": "User not found in model",
                    "user_id": user_id,
                    "model_available": True,
                    "suggestion": "User needs more interactions to be included in model",
                },
            }

        user_internal_id = self.user_id_map[user_id]

        try:
            # 1. Pobierz embedding użytkownika
            user_embedding = self.model.user_embeddings[user_internal_id].detach().cpu().numpy()

            # 2. Oblicz scores dla wszystkich książek
            all_book_embeddings = self.model.book_embeddings.detach().cpu().numpy()
            scores = np.dot(all_book_embeddings, user_embedding)

            # 3. Sortuj książki po score
            sorted_indices = np.argsort(-scores)  # Descending

            # 4. Filtruj wykluczonych
            exclude_set = set(exclude_book_ids or [])

            candidates = []
            for internal_id in sorted_indices:
                book_id_str = self.reverse_book_map.get(internal_id)

                if book_id_str is None:
                    continue

                if book_id_str in exclude_set:
                    continue

                candidates.append(
                    {
                        "_id": book_id_str,
                        "score": float(scores[internal_id]),
                        "rank": len(candidates) + 1,
                    }
                )

                # Zbierz 3x więcej kandydatów niż potrzeba (dla MMR)
                if len(candidates) >= n * 3:
                    break

            logger.info(
                f"🎯 LightGCN: {len(candidates)} kandydatów dla użytkownika {user_id[:8]}..."
            )

            # 5. MMR re-ranking (opcjonalne)
            if use_mmr and len(candidates) > n:
                logger.info(
                    f"🔄 Stosuję MMR re-ranking (λ={lambda_param}, author_limit={max_per_author})"
                )

                # Pobierz pełne info o książkach z bazy (potrzebne dla MMR)
                # TUTAJ MUSISZ DODAĆ POŁĄCZENIE Z MongoDB
                # candidates_with_metadata = await enrich_with_book_metadata(candidates)

                # Tymczasowo: zakładamy że candidates mają już 'genre', 'authors'
                # W prawdziwej implementacji dodaj to przez MongoDB query

                if offset > 0:
                    # Użyj wersji z offsetem
                    final_recommendations, next_offset = apply_mmr_with_offset(
                        candidates,
                        n=n,
                        offset=offset,
                        lambda_param=lambda_param,
                        embeddings_dict=self.book_embeddings_dict,
                        enforce_author_limit=enforce_author_limit,
                        max_per_author=max_per_author,
                    )

                    metadata = {
                        "model": "LightGCN + MMR",
                        "total_candidates": len(candidates),
                        "returned": len(final_recommendations),
                        "offset": offset,
                        "next_offset": next_offset,
                        "mmr_lambda": lambda_param,
                        "author_limit": max_per_author if enforce_author_limit else None,
                    }

                else:
                    # Standardowy MMR bez offset
                    final_recommendations = mmr_rerank(
                        candidates,
                        n=n,
                        lambda_param=lambda_param,
                        embeddings_dict=self.book_embeddings_dict,
                        enforce_author_limit=enforce_author_limit,
                        max_per_author=max_per_author,
                    )

                    # Oblicz metryki różnorodności
                    div_metrics = diversity_metrics(final_recommendations)

                    metadata = {
                        "model": "LightGCN + MMR",
                        "total_candidates": len(candidates),
                        "returned": len(final_recommendations),
                        "mmr_lambda": lambda_param,
                        "author_limit": max_per_author if enforce_author_limit else None,
                        "diversity_metrics": div_metrics,
                    }

            else:
                # Bez MMR - zwróć top N
                final_recommendations = candidates[:n]

                metadata = {
                    "model": "LightGCN (no MMR)",
                    "total_candidates": len(candidates),
                    "returned": len(final_recommendations),
                }

            logger.info(f"✅ Zwracam {len(final_recommendations)} rekomendacji")

            return {"recommendations": final_recommendations, "metadata": metadata}

        except Exception as e:
            logger.error(f"❌ Błąd generowania rekomendacji: {e}", exc_info=True)
            return {"recommendations": [], "metadata": {"error": str(e), "model_available": True}}


# ============================================================================
# GLOBALNA INSTANCJA SERWISU
# ============================================================================

_service_instance = None


def get_service() -> RecommendationService:
    """Singleton - zwraca globalną instancję serwisu"""
    global _service_instance
    if _service_instance is None:
        _service_instance = RecommendationService()
    return _service_instance


# ============================================================================
# FUNKCJE API (kompatybilność z istniejącym kodem)
# ============================================================================


def get_recommendations_for_goodbooks_user(
    user_id_str: str,
    n: int = 30,
    offset: int = 0,
    use_mmr: bool = True,
    lambda_param: float = 0.7,
    **kwargs,
) -> List[Dict]:
    """
    Główna funkcja API do rekomendacji.

    Args:
        user_id_str: MongoDB ObjectId użytkownika
        n: Liczba rekomendacji
        offset: Offset dla rotacji
        use_mmr: Czy użyć MMR
        lambda_param: Parametr MMR
        **kwargs: Dodatkowe argumenty (enforce_author_limit, max_per_author, etc.)

    Returns:
        Lista książek z rekomendacjami
    """
    service = get_service()
    result = service.get_recommendations(
        user_id=user_id_str,
        n=n,
        offset=offset,
        use_mmr=use_mmr,
        lambda_param=lambda_param,
        **kwargs,
    )

    return result["recommendations"]


def is_model_available() -> bool:
    """Sprawdza czy model jest dostępny"""
    service = get_service()
    return service.model_loaded


def get_model_stats() -> Dict:
    """Zwraca statystyki modelu"""
    service = get_service()

    if not service.model_loaded:
        return {"available": False, "error": "Model not loaded"}

    return {
        "available": True,
        "num_users": len(service.user_id_map),
        "num_books": len(service.book_id_map),
        "embedding_dim": (
            service.model.embedding_dim if hasattr(service.model, "embedding_dim") else None
        ),
        "model_path": str(MODEL_PATH),
    }
