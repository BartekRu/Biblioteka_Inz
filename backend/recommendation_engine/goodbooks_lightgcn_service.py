"""
goodbooks_lightgcn_service.py - ENHANCED WITH INCREMENTAL UPDATES

Rozszerzona wersja serwisu z real-time incremental learning.
Zachowuje pełną kompatybilność wsteczną z istniejącym API.

NOWE CECHY:
- Dynamiczne embeddingi użytkowników (SGD updates)
- Mapowanie MongoDB user_id → internal index
- Cache z invalidacją
- Periodic checkpoints
"""

from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import logging

import torch
import pandas as pd
import numpy as np

from .goodbooks_lightgcn import LightGCN, RATINGS_FILE, MODEL_DIR

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoodbooksLightGCNService:
    """
    Serwis do inferencji LightGCN trenowanego na goodbooks-10k.
    
    ENHANCED: Teraz z incremental learning!
    - Embeddingi użytkowników aktualizują się w czasie rzeczywistym
    - Nowi użytkownicy MongoDB dostają dynamiczny embedding
    - Cache z auto-invalidacją
    - Periodic checkpoints
    """

    def __init__(self) -> None:
        print("🔄 Inicjalizacja GoodbooksLightGCNService (Incremental Mode)...")
        
        # Podstawowe dane i model
        self._load_data_and_model()
        
        # 🆕 NOWE: Incremental learning state
        self._init_incremental_state()
        
        print("✅ GoodbooksLightGCNService gotowy (Incremental Mode aktywny).")

    def _load_data_and_model(self) -> None:
        """Ładuje bazowy model i dane (jak wcześniej)"""
        # ===== 1. Wczytanie ratings.csv i odtworzenie indeksów =====
        print(f"📥 Wczytuję ratings z {RATINGS_FILE}")
        df = pd.read_csv(RATINGS_FILE)

        # rating >= 3 => pozytyw
        df = df[df["rating"] >= 3].copy()

        # Enkodacja
        df["user_idx"] = df["user_id"].astype("category").cat.codes
        df["item_idx"] = df["book_id"].astype("category").cat.codes

        self.num_users = int(df["user_idx"].max() + 1)
        self.num_items = int(df["item_idx"].max() + 1)

        # ===== 2. Mappings item_idx <-> goodbooks_book_id =====
        mapping_df = df[["item_idx", "book_id"]].drop_duplicates()
        self.item_idx_to_book_id: Dict[int, int] = {
            int(row.item_idx): int(row.book_id) for row in mapping_df.itertuples()
        }
        self.book_id_to_item_idx: Dict[int, int] = {
            book_id: item_idx for item_idx, book_id in self.item_idx_to_book_id.items()
        }

        # ===== 3. Popularność itemów (fallback globalny) =====
        counts = df.groupby("item_idx").size()
        self.popular_item_indices: List[int] = (
            counts.sort_values(ascending=False).index.astype(int).tolist()
        )

        # ===== 4. edge_index na CPU =====
        users = torch.tensor(df["user_idx"].values, dtype=torch.long)
        items = torch.tensor(df["item_idx"].values, dtype=torch.long) + self.num_users
        rows = torch.cat([users, items], dim=0)
        cols = torch.cat([items, users], dim=0)
        self.edge_index = torch.stack([rows, cols], dim=0)

        # ===== 5. Załadowanie modelu =====
        model_path = Path(MODEL_DIR) / "lightgcn_goodbooks_pro.pt"
        if not model_path.exists():
            # Fallback do alternatywnej ścieżki
            model_path = Path(MODEL_DIR).parent / "trained_models" / "goodbooks_lightgcn_best.pt"
        
        if not model_path.exists():
            raise FileNotFoundError(
                f"Nie znaleziono wytrenowanego modelu.\n"
                f"Sprawdzone ścieżki:\n"
                f"  - {MODEL_DIR}/lightgcn_goodbooks_pro.pt\n"
                f"  - {MODEL_DIR}/../trained_models/goodbooks_lightgcn_best.pt"
            )

        print(f"📂 Ładuję model z: {model_path}")
        self.model = LightGCN(self.num_users, self.num_items)
        state = torch.load(model_path, map_location="cpu")
        self.model.load_state_dict(state)
        self.model.eval()

        # ===== 6. Prekomputacja embeddingów =====
        with torch.no_grad():
            user_emb, item_emb = self.model.propagate(self.edge_index)

        # 🆕 ZMIANA: Konwertuj na numpy dla łatwiejszych operacji
        self.user_emb_base = user_emb.cpu().numpy()  # Bazowe embeddingi
        self.item_emb = item_emb.cpu().numpy()       # Embeddingi książek (statyczne)
        
        # 🆕 Embedding dimension
        self.embedding_dim = self.item_emb.shape[1]
        
        print(f"   Base users: {self.num_users:,}")
        print(f"   Items: {self.num_items:,}")
        print(f"   Embedding dim: {self.embedding_dim}")

    def _init_incremental_state(self) -> None:
        """
        Inicjalizuj state dla incremental learning
        """
        # 🆕 Dynamiczne embeddingi (kopia bazowych + miejsce na nowych użytkowników)
        self.user_emb = self.user_emb_base.copy()
        
        # 🆕 Mapowanie MongoDB user_id <-> internal index
        self.mongo_user_to_idx: Dict[str, int] = {}
        self.idx_to_mongo_user: Dict[int, str] = {}
        
        # 🆕 Cache rekomendacji
        self.recommendations_cache: Dict[str, Tuple[List[int], datetime]] = {}
        self.cache_ttl_seconds = 300  # 5 minut
        
        # 🆕 Hiperparametry
        self.learning_rate = 0.001
        self.reg_lambda = 1e-4
        
        # 🆕 Statystyki
        self.total_updates = 0
        self.interactions_since_checkpoint = 0
        self.checkpoint_interval = 1000
        
        logger.info("✨ Incremental learning state initialized")
        logger.info(f"   Learning rate: {self.learning_rate}")
        logger.info(f"   Regularization: {self.reg_lambda}")
        logger.info(f"   Cache TTL: {self.cache_ttl_seconds}s")
        logger.info(f"   Checkpoint interval: {self.checkpoint_interval}")

    # =========================================================================
    # ORYGINALNE API (zachowane dla kompatybilności)
    # =========================================================================

    def recommend_for_goodbooks_ids(
        self,
        seed_book_ids: List[int],
        top_k: int = 20,
    ) -> List[int]:
        """
        ORYGINALNA METODA - bez zmian!
        
        Zwraca listę goodbooks_book_id rekomendowanych na podstawie seed_book_ids.
        Jeśli seed_book_ids jest puste => zwraca globalnie najpopularniejsze.
        """
        # Zamiana na item_idx
        seed_indices: List[int] = []
        for b in seed_book_ids:
            try:
                b_int = int(b)
            except (TypeError, ValueError):
                continue
            idx = self.book_id_to_item_idx.get(b_int)
            if idx is not None:
                seed_indices.append(idx)

        # Brak seedów -> globalny fallback
        if not seed_indices:
            indices = []
            for idx in self.popular_item_indices:
                if len(indices) >= top_k:
                    break
                indices.append(int(idx))
            return [self.item_idx_to_book_id[i] for i in indices]

        # Oblicz user vector jako średnia z seedów
        seed_embs = self.item_emb[seed_indices]  # numpy array
        user_vec = np.mean(seed_embs, axis=0)

        # Scores
        scores = np.dot(self.item_emb, user_vec)

        # Nie rekomenduj seedów
        scores[seed_indices] = -1e9

        # Top-k
        k = min(top_k, self.num_items)
        top_indices = np.argsort(scores)[-k:][::-1]

        result_ids: List[int] = []
        seen: Set[int] = set()

        for idx in top_indices:
            book_id = self.item_idx_to_book_id.get(int(idx))
            if book_id is None:
                continue
            if book_id in seen:
                continue
            seen.add(book_id)
            result_ids.append(int(book_id))
            if len(result_ids) >= top_k:
                break

        return result_ids

    # =========================================================================
    # 🆕 NOWE API - INCREMENTAL UPDATES
    # =========================================================================

    def get_or_create_user_idx(self, mongo_user_id: str) -> int:
        """
        Pobierz internal index dla użytkownika MongoDB lub stwórz nowy
        
        Args:
            mongo_user_id: ObjectId użytkownika z MongoDB (jako string)
            
        Returns:
            internal_idx: Index embeddingu użytkownika
        """
        # Jeśli już istnieje
        if mongo_user_id in self.mongo_user_to_idx:
            return self.mongo_user_to_idx[mongo_user_id]
        
        # Nowy użytkownik
        logger.info(f"🆕 Creating new user embedding for {mongo_user_id[:12]}...")
        
        new_idx = len(self.user_emb)
        
        # Inicjalizuj embedding (Xavier init)
        new_embedding = np.random.randn(1, self.embedding_dim) * np.sqrt(2.0 / self.embedding_dim)
        
        # Dodaj do tablicy
        self.user_emb = np.vstack([self.user_emb, new_embedding])
        
        # Zapisz mapowanie
        self.mongo_user_to_idx[mongo_user_id] = new_idx
        self.idx_to_mongo_user[new_idx] = mongo_user_id
        
        logger.info(f"   New user idx: {new_idx}, Total users: {len(self.user_emb):,}")
        
        return new_idx

    def update_user_embedding(
        self,
        user_idx: int,
        goodbooks_book_id: int,
        interaction_type: str = "borrow"
    ) -> Dict:
        """
        Aktualizuj embedding użytkownika po nowej interakcji (SGD step)
        
        Args:
            user_idx: Internal index użytkownika
            goodbooks_book_id: ID książki z goodbooks-10k
            interaction_type: "borrow", "review", "view"
            
        Returns:
            Dict z informacjami o update
        """
        # Mapuj goodbooks_id → item_idx
        item_idx = self.book_id_to_item_idx.get(goodbooks_book_id)
        
        if item_idx is None:
            return {
                "success": False,
                "reason": "book_not_in_model",
                "goodbooks_book_id": goodbooks_book_id
            }
        
        # Wagi dla różnych typów interakcji
        interaction_weights = {
            "borrow": 1.0,
            "review": 0.8,
            "view": 0.3
        }
        weight = interaction_weights.get(interaction_type, 0.5)
        
        # Embeddingi
        user_emb = self.user_emb[user_idx]
        book_emb = self.item_emb[item_idx]
        
        # Score przed
        score_before = np.dot(user_emb, book_emb)
        
        # Target score
        target = weight
        
        # Błąd
        error = target - score_before
        
        # Gradient z L2 regularization
        gradient = -error * book_emb + self.reg_lambda * user_emb
        
        # SGD update
        update_delta = self.learning_rate * gradient
        self.user_emb[user_idx] -= update_delta
        
        # Normalizacja (zapobieganie exploding gradients)
        norm = np.linalg.norm(self.user_emb[user_idx])
        if norm > 10.0:
            self.user_emb[user_idx] /= (norm / 10.0)
        
        # Score po
        score_after = np.dot(self.user_emb[user_idx], book_emb)
        
        # Statystyki
        self.total_updates += 1
        self.interactions_since_checkpoint += 1
        
        logger.debug(f"📈 Updated user {user_idx}: score {score_before:.4f} → {score_after:.4f}")
        
        return {
            "success": True,
            "user_idx": user_idx,
            "item_idx": item_idx,
            "score_before": float(score_before),
            "score_after": float(score_after),
            "error": float(error),
            "update_magnitude": float(np.linalg.norm(update_delta)),
            "total_updates": self.total_updates
        }

    def process_interaction(
        self,
        mongo_user_id: str,
        goodbooks_book_id: int,
        interaction_type: str = "borrow"
    ) -> Dict:
        """
        Główna funkcja - przetwarza interakcję i aktualizuje embeddingi
        
        Pipeline:
        1. Mapuj user_id → user_idx (lub stwórz nowy)
        2. Wykonaj SGD update embeddingu
        3. Invaliduj cache użytkownika
        4. Sprawdź czy pora na checkpoint
        
        Args:
            mongo_user_id: MongoDB ObjectId użytkownika (string)
            goodbooks_book_id: ID książki z goodbooks-10k
            interaction_type: "borrow", "review", "view"
            
        Returns:
            Dict z informacjami o przetworzeniu
        """
        logger.info(
            f"⚡ Processing: user={mongo_user_id[:12]}..., "
            f"book={goodbooks_book_id}, type={interaction_type}"
        )
        
        # 1. User index
        user_idx = self.get_or_create_user_idx(mongo_user_id)
        
        # 2. Update embedding
        update_info = self.update_user_embedding(
            user_idx=user_idx,
            goodbooks_book_id=goodbooks_book_id,
            interaction_type=interaction_type
        )
        
        if not update_info["success"]:
            return update_info
        
        # 3. Invalidate cache
        self.invalidate_user_cache(mongo_user_id)
        
        # 4. Checkpoint?
        if self.interactions_since_checkpoint >= self.checkpoint_interval:
            logger.info("🔔 Checkpoint threshold reached - saving...")
            self.save_checkpoint()
        
        return {
            **update_info,
            "checkpoint_saved": self.interactions_since_checkpoint == 0
        }

    def get_recommendations_for_user(
        self,
        mongo_user_id: str,
        n: int = 20,
        exclude_goodbooks_ids: Optional[Set[int]] = None,
        use_cache: bool = True
    ) -> List[int]:
        """
        Pobierz rekomendacje dla użytkownika (z cache)
        
        Args:
            mongo_user_id: MongoDB user ID (string)
            n: Liczba rekomendacji
            exclude_goodbooks_ids: Set goodbooks_id do wykluczenia
            use_cache: Czy używać cache
            
        Returns:
            Lista goodbooks_book_id
        """
        cache_key = f"{mongo_user_id}:{n}"
        
        # Cache check
        if use_cache and cache_key in self.recommendations_cache:
            cached_recs, cached_time = self.recommendations_cache[cache_key]
            age_seconds = (datetime.now() - cached_time).total_seconds()
            
            if age_seconds < self.cache_ttl_seconds:
                logger.debug(f"💾 Cache hit for user {mongo_user_id[:12]} (age: {age_seconds:.1f}s)")
                return cached_recs
        
        # Oblicz rekomendacje
        user_idx = self.get_or_create_user_idx(mongo_user_id)
        
        # User embedding
        user_emb = self.user_emb[user_idx]
        
        # Scores = item_emb · user_emb
        scores = np.dot(self.item_emb, user_emb)
        
        # Wykluczenie
        if exclude_goodbooks_ids:
            for gb_id in exclude_goodbooks_ids:
                item_idx = self.book_id_to_item_idx.get(gb_id)
                if item_idx is not None:
                    scores[item_idx] = -1e9
        
        # Top-N
        top_indices = np.argsort(scores)[-n:][::-1]
        
        # Mapowanie do goodbooks_id
        result_ids: List[int] = []
        seen: Set[int] = set()
        
        for idx in top_indices:
            book_id = self.item_idx_to_book_id.get(int(idx))
            if book_id is None:
                continue
            if book_id in seen:
                continue
            seen.add(book_id)
            result_ids.append(int(book_id))
            if len(result_ids) >= n:
                break
        
        # Zapisz do cache
        self.recommendations_cache[cache_key] = (result_ids, datetime.now())
        
        logger.debug(f"🎯 Generated {len(result_ids)} recommendations for user {mongo_user_id[:12]}")
        
        return result_ids

    def invalidate_user_cache(self, mongo_user_id: str):
        """Usuń cache rekomendacji dla użytkownika"""
        keys_to_remove = [
            k for k in self.recommendations_cache.keys() 
            if k.startswith(f"{mongo_user_id}:")
        ]
        for key in keys_to_remove:
            del self.recommendations_cache[key]
        
        if keys_to_remove:
            logger.debug(f"🗑️  Invalidated cache for user {mongo_user_id[:12]} ({len(keys_to_remove)} entries)")

    def save_checkpoint(self):
        """Zapisz aktualny stan embeddingów do pliku"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_path = Path(MODEL_DIR) / f"lightgcn_goodbooks_incremental_{timestamp}.npy"
        
        logger.info(f"💾 Saving checkpoint to {checkpoint_path}")
        
        # Zapisz jako numpy array
        checkpoint_data = {
            'user_emb': self.user_emb,
            'mongo_user_to_idx': self.mongo_user_to_idx,
            'idx_to_mongo_user': self.idx_to_mongo_user,
            'total_updates': self.total_updates,
            'timestamp': timestamp
        }
        
        np.save(checkpoint_path, checkpoint_data, allow_pickle=True)
        
        # Reset counter
        self.interactions_since_checkpoint = 0
        
        logger.info(f"✅ Checkpoint saved! Total updates: {self.total_updates:,}")

    def get_stats(self) -> Dict:
        """Pobierz statystyki serwisu"""
        return {
            "base_users": self.num_users,
            "total_users": len(self.user_emb),
            "new_users_created": len(self.mongo_user_to_idx),
            "total_items": self.num_items,
            "total_updates": self.total_updates,
            "interactions_since_checkpoint": self.interactions_since_checkpoint,
            "cache_size": len(self.recommendations_cache),
            "embedding_dim": self.embedding_dim,
            "learning_rate": self.learning_rate,
            "incremental_mode": True
        }


# Singleton - wczyta się raz przy starcie backendu
goodbooks_lgcn_service = GoodbooksLightGCNService()