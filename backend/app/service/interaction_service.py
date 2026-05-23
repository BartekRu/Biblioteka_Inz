"""
services/interaction_service.py
Centralized service for managing ALL user interactions: view, borrow, review
"""

from datetime import datetime, timedelta
from typing import Optional, Dict
from motor.motor_asyncio import AsyncIOMotorCollection
import logging

logger = logging.getLogger(__name__)

INTERACTION_WEIGHTS = {
    "view": 0.1,
    "review": 0.8,
    "borrow": 1.0,
    "wishlist_add": 0.5,
    "wishlist_remove": 0.0,
}

DEDUP_WINDOWS = {
    "view": timedelta(minutes=15),
    "borrow": timedelta(minutes=2),
    "wishlist_add": timedelta(minutes=2),
    "wishlist_remove": timedelta(minutes=2),
}


class InteractionService:
    """
    Centralized interaction management
    - Jedna kolekcja `interactions`
    - LightGCN czyta bezpośrednio z tej kolekcji
    - Aktualizuje embeddingi przez adapter (opcjonalnie)
    """

    def __init__(
        self,
        interactions_collection: AsyncIOMotorCollection,
        recommendation_service,  # Może być LightGCNAdapter lub None
    ):
        self.interactions = interactions_collection
        self.rec_service = recommendation_service

        # Sprawdź czy mamy aktywny serwis rekomendacji
        self.embeddings_enabled = recommendation_service is not None

        if not self.embeddings_enabled:
            logger.warning(
                "⚠️  InteractionService initialized WITHOUT recommendation service - "
                "embeddings will NOT be updated"
            )

    async def create_interaction(
        self,
        user_id: str,
        book_id: str,
        interaction_type: str,
        metadata: Optional[Dict] = None,
        update_embedding: bool = True,
    ) -> Dict:
        """
        Tworzy nową interakcję i opcjonalnie aktualizuje embeddingi

        Args:
            user_id: MongoDB user_id
            book_id: MongoDB book_id
            interaction_type: 'view', 'review', lub 'borrow'
            metadata: Dodatkowe dane (opcjonalne)
            update_embedding: Czy aktualizować embeddingi (domyślnie True)

        Returns:
            Dict z wynikami: interaction_id, weight, embedding_updated, etc.
        """
        # 🔒 Walidacja typu
        if interaction_type not in INTERACTION_WEIGHTS:
            raise ValueError(f"Invalid interaction type: {interaction_type}")

        weight = INTERACTION_WEIGHTS[interaction_type]
        embedding_updated = False
        embedding_result = None
        now = datetime.utcnow()

        dedup_window = DEDUP_WINDOWS.get(interaction_type)
        if dedup_window:
            recent = await self.interactions.find_one(
                {
                    "user_id": user_id,
                    "book_id": book_id,
                    "interaction_type": interaction_type,
                    "created_at": {"$gte": now - dedup_window},
                },
                sort=[("created_at", -1)],
            )
            if recent:
                logger.info(
                    "Skipping duplicate interaction | %s | user=%s book=%s",
                    interaction_type,
                    user_id[:12],
                    book_id[:12],
                )
                return {
                    "interaction_id": str(recent["_id"]),
                    "interaction_type": interaction_type,
                    "weight": weight,
                    "embedding_updated": False,
                    "embedding_result": None,
                    "created_at": recent.get("created_at"),
                    "deduplicated": True,
                }

        interaction_doc = {
            "user_id": user_id,
            "book_id": book_id,
            "interaction_type": interaction_type,
            "weight": weight,
            "metadata": metadata or {},
            "created_at": now,
            "embedding_updated": False,
        }

        # 1️⃣ Zapis do DB (ZAWSZE)
        result = await self.interactions.insert_one(interaction_doc)

        logger.info(
            f"✅ Interaction created | {interaction_type} | "
            f"user={user_id[:12]}... book={book_id[:12]}... weight={weight}"
        )

        # 2️⃣ Aktualizacja embeddingów (opcjonalna)
        if update_embedding and self.embeddings_enabled:
            try:
                embedding_result = await self.rec_service.update_user_embedding_incremental(
                    user_id=user_id,
                    book_id=book_id,
                    interaction_weight=weight,
                )

                if embedding_result and embedding_result.get("success"):
                    embedding_updated = True

                    # Oznacz w DB że embedding został zaktualizowany
                    await self.interactions.update_one(
                        {"_id": result.inserted_id},
                        {"$set": {"embedding_updated": True}},
                    )

                    logger.info(
                        f"🧠 Embedding updated for user={user_id[:12]}... "
                        f"(total_updates={embedding_result.get('total_updates', '?')})"
                    )
                else:
                    reason = (
                        embedding_result.get("reason", "unknown")
                        if embedding_result
                        else "no_result"
                    )
                    logger.warning(
                        f"⚠️  Embedding NOT updated: user={user_id[:12]}... "
                        f"book={book_id[:12]}... reason={reason}"
                    )

            except Exception as e:
                logger.error(f"❌ Embedding update failed: {e}", exc_info=True)

        elif update_embedding and not self.embeddings_enabled:
            logger.debug("⚠️  Embedding update skipped - recommendation service not available")

        return {
            "interaction_id": str(result.inserted_id),
            "interaction_type": interaction_type,
            "weight": weight,
            "embedding_updated": embedding_updated,
            "embedding_result": embedding_result,  # Pełne info z adaptera
            "created_at": interaction_doc["created_at"],
        }

    async def get_user_interactions(
        self,
        user_id: str,
        interaction_type: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        """Pobiera interakcje użytkownika"""
        query = {"user_id": user_id}
        if interaction_type:
            query["interaction_type"] = interaction_type

        cursor = self.interactions.find(query).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_all_interactions_for_training(self) -> list:
        """
        Pełny zbiór interakcji do treningu LightGCN
        """
        interactions = await self.interactions.find({}).to_list(length=None)

        stats = {}
        for inter in interactions:
            t = inter.get("interaction_type", "unknown")
            stats[t] = stats.get(t, 0) + 1

        logger.info(f"📊 Loaded {len(interactions)} interactions")
        logger.info(f"📊 Breakdown: {stats}")

        return interactions

    async def get_embedding_stats(self) -> Dict:
        """
        Statystyki dotyczące aktualizacji embeddingów
        """
        total = await self.interactions.count_documents({})
        updated = await self.interactions.count_documents({"embedding_updated": True})

        # Per typ
        stats_by_type = {}
        for itype in INTERACTION_WEIGHTS.keys():
            type_total = await self.interactions.count_documents({"interaction_type": itype})
            type_updated = await self.interactions.count_documents(
                {"interaction_type": itype, "embedding_updated": True}
            )
            stats_by_type[itype] = {
                "total": type_total,
                "embedding_updated": type_updated,
                "update_rate": round(type_updated / type_total * 100, 2) if type_total > 0 else 0,
            }

        return {
            "total_interactions": total,
            "embeddings_updated": updated,
            "update_rate_percent": round(updated / total * 100, 2) if total > 0 else 0,
            "embeddings_enabled": self.embeddings_enabled,
            "by_type": stats_by_type,
        }
