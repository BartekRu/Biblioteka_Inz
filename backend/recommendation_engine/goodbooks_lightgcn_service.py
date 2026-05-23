from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import logging

import torch
import pandas as pd
import numpy as np
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from .goodbooks_lightgcn import LightGCN, RATINGS_FILE, MODEL_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoodbooksLightGCNService:

    def __init__(self, db=None) -> None:
        print("🔄 Inicjalizacja GoodbooksLightGCNService (MongoDB Persistence)...")

        self.db = db

        self._load_data_and_model()

        self._init_incremental_state()

        if self.db is not None:
            import asyncio

            asyncio.create_task(self._load_embeddings_from_db())

        print("✅ GoodbooksLightGCNService gotowy (MongoDB Persistence aktywna).")

    def _load_data_and_model(self) -> None:
        print(f"📥 Wczytuję ratings z {RATINGS_FILE}")
        df = pd.read_csv(RATINGS_FILE)

        df = df[df["rating"] >= 3].copy()

        df["user_idx"] = df["user_id"].astype("category").cat.codes
        df["item_idx"] = df["book_id"].astype("category").cat.codes

        self.num_users = int(df["user_idx"].max() + 1)
        self.num_items = int(df["item_idx"].max() + 1)

        mapping_df = df[["item_idx", "book_id"]].drop_duplicates()
        self.item_idx_to_book_id: Dict[int, int] = {
            int(row.item_idx): int(row.book_id) for row in mapping_df.itertuples()
        }
        self.book_id_to_item_idx: Dict[int, int] = {
            book_id: item_idx for item_idx, book_id in self.item_idx_to_book_id.items()
        }

        counts = df.groupby("item_idx").size()
        self.popular_item_indices: List[int] = (
            counts.sort_values(ascending=False).index.astype(int).tolist()
        )

        users = torch.tensor(df["user_idx"].values, dtype=torch.long)
        items = torch.tensor(df["item_idx"].values, dtype=torch.long) + self.num_users
        rows = torch.cat([users, items], dim=0)
        cols = torch.cat([items, users], dim=0)
        self.edge_index = torch.stack([rows, cols], dim=0)

        model_path = Path(MODEL_DIR) / "lightgcn_goodbooks_pro.pt"
        if not model_path.exists():
            model_path = Path(MODEL_DIR).parent / "trained_models" / "goodbooks_lightgcn_best.pt"

        if not model_path.exists():
            raise FileNotFoundError(f"Nie znaleziono modelu w {MODEL_DIR}")

        print(f"📂 Ładuję model z: {model_path}")
        self.model = LightGCN(self.num_users, self.num_items)
        state = torch.load(model_path, map_location="cpu")
        self.model.load_state_dict(state)
        self.model.eval()

        with torch.no_grad():
            user_emb, item_emb = self.model.propagate(self.edge_index)

        self.user_emb_base = user_emb.cpu().numpy()
        self.item_emb = item_emb.cpu().numpy()
        self.embedding_dim = self.item_emb.shape[1]

        print(f"   Base users: {self.num_users:,}")
        print(f"   Items: {self.num_items:,}")
        print(f"   Embedding dim: {self.embedding_dim}")

    def _init_incremental_state(self) -> None:
        self.user_emb = self.user_emb_base.copy()
        self.mongo_user_to_idx: Dict[str, int] = {}
        self.idx_to_mongo_user: Dict[int, str] = {}
        self.recommendations_cache: Dict[str, Tuple[List[int], datetime]] = {}
        self.cache_ttl_seconds = 300
        self.learning_rate = 0.001
        self.reg_lambda = 1e-4
        self.total_updates = 0
        self.interactions_since_checkpoint = 0
        self.checkpoint_interval = 1000

        self.user_interaction_counts: Dict[str, int] = defaultdict(int)

        self.user_last_update: Dict[str, datetime] = {}

        logger.info("✨ Incremental learning state initialized")

    async def _load_embeddings_from_db(self):

        if self.db is None:
            logger.warning("⚠️  Brak połączenia z DB - pomijam ładowanie embeddingów")
            return

        try:
            count = 0
            cursor = self.db.user_embeddings.find({})

            async for doc in cursor:
                user_id = doc["user_id"]
                user_idx = doc["user_idx"]
                embedding = np.array(doc["embedding"], dtype=np.float32)

                if user_idx >= len(self.user_emb):
                    needed_rows = user_idx - len(self.user_emb) + 1
                    new_embeddings = np.random.randn(needed_rows, self.embedding_dim) * np.sqrt(
                        2.0 / self.embedding_dim
                    )
                    self.user_emb = np.vstack([self.user_emb, new_embeddings])

                self.user_emb[user_idx] = embedding

                self.mongo_user_to_idx[user_id] = user_idx
                self.idx_to_mongo_user[user_idx] = user_id

                self.user_interaction_counts[user_id] = doc.get("interactions_count", 0)
                self.user_last_update[user_id] = doc.get("last_updated", datetime.utcnow())

                count += 1

            logger.info(f"✅ Załadowano {count:,} embeddingów użytkowników z MongoDB")

        except Exception as e:
            logger.error(f"❌ Błąd przy ładowaniu embeddingów: {e}")
            import traceback

            traceback.print_exc()

    async def _save_user_embedding_to_db(self, user_id: str, user_idx: int):

        if self.db is None:
            return

        try:
            embedding = self.user_emb[user_idx]

            doc = {
                "user_id": user_id,
                "user_idx": user_idx,
                "embedding": embedding.tolist(),
                "interactions_count": self.user_interaction_counts.get(user_id, 0),
                "last_updated": datetime.utcnow(),
                "embedding_norm": float(np.linalg.norm(embedding)),
                "is_new_user": user_idx >= self.num_users,
            }

            await self.db.user_embeddings.update_one(
                {"user_id": user_id}, {"$set": doc}, upsert=True
            )

            logger.debug(f"💾 Zapisano embedding dla {user_id[:12]}...")

        except Exception as e:
            logger.error(f"❌ Błąd przy zapisie embeddingu: {e}")

    async def sync_interactions_from_db(self, max_interactions: int = 10000):

        if self.db is None:
            logger.warning("⚠️  Brak połączenia z DB - pomijam sync interakcji")
            return

        try:
            cursor = self.db.interactions.find().sort("timestamp", -1).limit(max_interactions)

            interactions_processed = 0
            interactions_skipped = 0

            async for doc in cursor:
                try:
                    user_id = str(doc["user_id"])
                    book_mongo_id = str(doc["book_id"])
                    interaction_type = doc.get("interaction_type", "view")

                    book = await self.db.books.find_one({"_id": ObjectId(book_mongo_id)})
                    if not book or not book.get("goodbooks_book_id"):
                        interactions_skipped += 1
                        continue

                    goodbooks_id = int(book["goodbooks_book_id"])

                    self._process_interaction_internal(
                        user_id=user_id,
                        goodbooks_id=goodbooks_id,
                        interaction_type=interaction_type,
                        save_to_db=False,
                    )

                    interactions_processed += 1

                except Exception as e:
                    logger.debug(f"Pominięto interakcję: {e}")
                    interactions_skipped += 1

            logger.info(
                f"✅ Zsynchronizowano {interactions_processed:,} interakcji "
                f"(pominięto: {interactions_skipped:,})"
            )

        except Exception as e:
            logger.error(f"❌ Błąd przy synchronizacji interakcji: {e}")

    def get_or_create_user_idx(self, mongo_user_id: str) -> int:
        """Pobierz lub stwórz index użytkownika"""
        if mongo_user_id in self.mongo_user_to_idx:
            return self.mongo_user_to_idx[mongo_user_id]

        logger.info(f"🆕 Creating new user embedding for {mongo_user_id[:12]}...")

        new_idx = len(self.user_emb)
        new_embedding = np.random.randn(1, self.embedding_dim) * np.sqrt(2.0 / self.embedding_dim)
        self.user_emb = np.vstack([self.user_emb, new_embedding])

        self.mongo_user_to_idx[mongo_user_id] = new_idx
        self.idx_to_mongo_user[new_idx] = mongo_user_id

        logger.info(f"   New user idx: {new_idx}, Total users: {len(self.user_emb):,}")

        return new_idx

    def _process_interaction_internal(
        self, user_id: str, goodbooks_id: int, interaction_type: str, save_to_db: bool = True
    ) -> Dict:

        item_idx = self.book_id_to_item_idx.get(goodbooks_id)

        if item_idx is None:
            return {
                "success": False,
                "reason": "book_not_in_model",
                "goodbooks_book_id": goodbooks_id,
            }

        user_idx = self.get_or_create_user_idx(user_id)

        interaction_weights = {"borrow": 1.0, "review": 0.8, "reserve": 0.6, "view": 0.1}
        weight = interaction_weights.get(interaction_type, 0.5)

        user_emb = self.user_emb[user_idx]
        book_emb = self.item_emb[item_idx]

        score_before = np.dot(user_emb, book_emb)

        target = weight
        error = target - score_before
        gradient = -error * book_emb + self.reg_lambda * user_emb
        update_delta = self.learning_rate * gradient
        self.user_emb[user_idx] -= update_delta

        norm = np.linalg.norm(self.user_emb[user_idx])
        if norm > 10.0:
            self.user_emb[user_idx] /= norm / 10.0

        score_after = np.dot(self.user_emb[user_idx], book_emb)

        self.total_updates += 1
        self.interactions_since_checkpoint += 1
        self.user_interaction_counts[user_id] += 1
        self.user_last_update[user_id] = datetime.utcnow()

        if save_to_db and self.db is not None:
            import asyncio

            loop = asyncio.get_event_loop()
            loop.create_task(self._save_user_embedding_to_db(user_id, user_idx))

        logger.debug(f"📈 Updated user {user_idx}: score {score_before:.4f} → {score_after:.4f}")

        return {
            "success": True,
            "user_idx": user_idx,
            "item_idx": item_idx,
            "score_before": float(score_before),
            "score_after": float(score_after),
            "error": float(error),
            "update_magnitude": float(np.linalg.norm(update_delta)),
            "total_updates": self.total_updates,
        }

    def process_interaction(
        self, mongo_user_id: str, goodbooks_book_id: int, interaction_type: str = "borrow"
    ) -> Dict:

        logger.info(
            f"⚡ Processing: user={mongo_user_id[:12]}..., "
            f"book={goodbooks_book_id}, type={interaction_type}"
        )

        update_info = self._process_interaction_internal(
            user_id=mongo_user_id,
            goodbooks_id=goodbooks_book_id,
            interaction_type=interaction_type,
            save_to_db=True,
        )

        if not update_info["success"]:
            return update_info

        self.invalidate_user_cache(mongo_user_id)

        if self.interactions_since_checkpoint >= self.checkpoint_interval:
            logger.info("🔔 Checkpoint threshold reached...")
            self.interactions_since_checkpoint = 0

        return {**update_info, "interaction_count": self.user_interaction_counts[mongo_user_id]}

    def get_recommendations_for_user(
        self,
        mongo_user_id: str,
        n: int = 20,
        exclude_goodbooks_ids: Optional[Set[int]] = None,
        use_cache: bool = True,
    ) -> List[int]:
        cache_key = f"{mongo_user_id}:{n}"

        if use_cache and cache_key in self.recommendations_cache:
            cached_recs, cached_time = self.recommendations_cache[cache_key]
            age_seconds = (datetime.now() - cached_time).total_seconds()

            if age_seconds < self.cache_ttl_seconds:
                logger.debug(
                    f"💾 Cache hit for user {mongo_user_id[:12]} (age: {age_seconds:.1f}s)"
                )
                return cached_recs

        user_idx = self.get_or_create_user_idx(mongo_user_id)
        user_emb = self.user_emb[user_idx]
        scores = np.dot(self.item_emb, user_emb)

        if exclude_goodbooks_ids:
            for gb_id in exclude_goodbooks_ids:
                item_idx = self.book_id_to_item_idx.get(gb_id)
                if item_idx is not None:
                    scores[item_idx] = -1e9

        top_indices = np.argsort(scores)[-n:][::-1]

        result_ids: List[int] = []
        seen: Set[int] = set()

        for idx in top_indices:
            book_id = self.item_idx_to_book_id.get(int(idx))
            if book_id is None or book_id in seen:
                continue
            seen.add(book_id)
            result_ids.append(int(book_id))
            if len(result_ids) >= n:
                break

        self.recommendations_cache[cache_key] = (result_ids, datetime.now())

        return result_ids

    def invalidate_user_cache(self, mongo_user_id: str):
        keys_to_remove = [
            k for k in self.recommendations_cache.keys() if k.startswith(f"{mongo_user_id}:")
        ]
        for key in keys_to_remove:
            del self.recommendations_cache[key]

    def get_stats(self) -> Dict:
        return {
            "base_users": self.num_users,
            "total_users": len(self.user_emb),
            "new_users_created": len(self.mongo_user_to_idx),
            "total_items": self.num_items,
            "total_updates": self.total_updates,
            "interactions_since_checkpoint": self.interactions_since_checkpoint,
            "checkpoint_interval": self.checkpoint_interval,
            "cache_size": len(self.recommendations_cache),
            "embedding_dim": self.embedding_dim,
            "learning_rate": self.learning_rate,
            "incremental_mode": True,
            "mongodb_persistence": self.db is not None,
        }

    def recommend_for_goodbooks_ids(
        self,
        seed_book_ids: List[int],
        top_k: int = 20,
    ) -> List[int]:
        seed_indices: List[int] = []
        for b in seed_book_ids:
            try:
                b_int = int(b)
            except (TypeError, ValueError):
                continue
            idx = self.book_id_to_item_idx.get(b_int)
            if idx is not None:
                seed_indices.append(idx)

        if not seed_indices:
            return [self.item_idx_to_book_id[i] for i in self.popular_item_indices[:top_k]]

        seed_embs = self.item_emb[seed_indices]
        user_vec = np.mean(seed_embs, axis=0)
        scores = np.dot(self.item_emb, user_vec)
        scores[seed_indices] = -1e9

        k = min(top_k, self.num_items)
        top_indices = np.argsort(scores)[-k:][::-1]

        result_ids: List[int] = []
        seen: Set[int] = set()

        for idx in top_indices:
            book_id = self.item_idx_to_book_id.get(int(idx))
            if book_id is None or book_id in seen:
                continue
            seen.add(book_id)
            result_ids.append(int(book_id))
            if len(result_ids) >= top_k:
                break

        return result_ids


_service_instance = None


def get_service(db=None):
    """Pobierz singleton serwisu"""
    global _service_instance
    if _service_instance is None:
        _service_instance = GoodbooksLightGCNService(db=db)
    elif db is not None and _service_instance.db is None:
        _service_instance.db = db

        import asyncio

        loop = asyncio.get_event_loop()
        loop.create_task(_service_instance._load_embeddings_from_db())

    return _service_instance


goodbooks_lgcn_service = None
