

from pathlib import Path
from typing import List, Dict, Set

import torch
import pandas as pd

from .goodbooks_lightgcn import LightGCN, RATINGS_FILE, MODEL_DIR

class GoodbooksLightGCNService:
    """
    Serwis do inferencji LightGCN trenowanego na goodbooks-10k.
    Ładuje:
    - ratings.csv (rating >= 3)
    - wytrenowany model lightgcn_goodbooks_pro.pt
    - embeddings użytkowników i książek

    Udostępnia:
    - recommend_for_goodbooks_ids(seed_book_ids) -> lista goodbooks_book_id
    """

    def __init__(self) -> None:
        print("🔄 Inicjalizacja GoodbooksLightGCNService...")
        self._load_data_and_model()
        print("✅ GoodbooksLightGCNService gotowy.")

    def _load_data_and_model(self) -> None:
        # ===== 1. Wczytanie ratings.csv i odtworzenie indeksów =====
        print(f"📥 Wczytuję ratings z {RATINGS_FILE}")
        df = pd.read_csv(RATINGS_FILE)

        # Tak samo jak w treningu: rating >= 3 => pozytyw
        df = df[df["rating"] >= 3].copy()

        # Dokładnie ta sama enkodacja co w treningu:
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
        # posortowane od najpopularniejszych
        self.popular_item_indices: List[int] = (
            counts.sort_values(ascending=False).index.astype(int).tolist()
        )

        # ===== 4. edge_index na CPU =====
        users = torch.tensor(df["user_idx"].values, dtype=torch.long)
        items = torch.tensor(df["item_idx"].values, dtype=torch.long) + self.num_users
        rows = torch.cat([users, items], dim=0)
        cols = torch.cat([items, users], dim=0)
        self.edge_index = torch.stack([rows, cols], dim=0)  # [2, E]

        # ===== 5. Załadowanie modelu =====
        model_path = Path(MODEL_DIR) / "lightgcn_goodbooks_pro.pt"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Nie znaleziono wytrenowanego modelu: {model_path}.\n"
                f"Upewnij się, że trening goodbooks_lightgcn został uruchomiony "
                f"i plik się zapisał."
            )

        self.model = LightGCN(self.num_users, self.num_items)
        state = torch.load(model_path, map_location="cpu")
        self.model.load_state_dict(state)
        self.model.eval()

        # ===== 6. Prekomputacja embeddingów =====
        with torch.no_grad():
            user_emb, item_emb = self.model.propagate(self.edge_index)

        # Trzymamy wszystko na CPU
        self.user_emb = user_emb.cpu()
        self.item_emb = item_emb.cpu()

    # ----------------------------------------------------------
    #  API serwisu
    # ----------------------------------------------------------
    def recommend_for_goodbooks_ids(
        self,
        seed_book_ids: List[int],
        top_k: int = 20,
    ) -> List[int]:
        """
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

        seed_tensor = torch.tensor(seed_indices, dtype=torch.long)
        seed_embs = self.item_emb[seed_tensor]  # [S, dim]
        user_vec = seed_embs.mean(dim=0)        # [dim]

        # scores = item_emb ⋅ user_vec
        scores = torch.matmul(self.item_emb, user_vec)  # [num_items]

        # nie rekomenduj już "seedów"
        scores[seed_tensor] = -1e9

        # Top-k
        k = min(top_k, self.num_items)
        top_scores, top_indices = torch.topk(scores, k=k)

        result_ids: List[int] = []
        seen: Set[int] = set()

        for idx in top_indices.tolist():
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


# Singleton serwisu – wczyta się raz przy starcie backendu
goodbooks_lgcn_service = GoodbooksLightGCNService()
