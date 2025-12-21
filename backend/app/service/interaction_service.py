"""
services/interaction_service.py
Centralized service for managing ALL user interactions: view, borrow, review
"""

from datetime import datetime
from typing import Optional, Dict
from motor.motor_asyncio import AsyncIOMotorCollection
import logging

logger = logging.getLogger(__name__)

INTERACTION_WEIGHTS = {
    "view": 0.3,
    "review": 0.8,
    "borrow": 1.0,
}


class InteractionService:
    """
    Centralized interaction management
    - Jedna kolekcja `interactions`
    - LightGCN czyta bezpośrednio z tej kolekcji
    """

    def __init__(
        self,
        interactions_collection: AsyncIOMotorCollection,
        recommendation_service,
    ):
        self.interactions = interactions_collection
        self.rec_service = recommendation_service

    async def create_interaction(
        self,
        user_id: str,
        book_id: str,
        interaction_type: str,
        metadata: Optional[Dict] = None,
        update_embedding: bool = True,
    ) -> Dict:
        # 🔒 Walidacja typu
        if interaction_type not in INTERACTION_WEIGHTS:
            raise ValueError(f"Invalid interaction type: {interaction_type}")

        weight = INTERACTION_WEIGHTS[interaction_type]
        embedding_updated = False

        interaction_doc = {
            "user_id": user_id,
            "book_id": book_id,
            "interaction_type": interaction_type,
            "weight": weight,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "embedding_updated": False,
        }

        # 1️⃣ Zapis do DB (ZAWSZE)
        result = await self.interactions.insert_one(interaction_doc)

        logger.info(
            f"✅ Interaction created | {interaction_type} | "
            f"user={user_id} book={book_id} weight={weight}"
        )

        # 2️⃣ Aktualizacja embeddingów (opcjonalna)
        if update_embedding:
            try:
                await self.rec_service.update_user_embedding_incremental(
                    user_id=user_id,
                    book_id=book_id,
                    interaction_weight=weight,
                )

                embedding_updated = True

                await self.interactions.update_one(
                    {"_id": result.inserted_id},
                    {"$set": {"embedding_updated": True}},
                )

                logger.info(f"🧠 Embedding updated for user={user_id}")

            except Exception as e:
                logger.error(f"❌ Embedding update failed: {e}")

        return {
            "interaction_id": str(result.inserted_id),
            "interaction_type": interaction_type,
            "weight": weight,
            "embedding_updated": embedding_updated,
            "created_at": interaction_doc["created_at"],
        }

    async def get_user_interactions(
        self,
        user_id: str,
        interaction_type: Optional[str] = None,
        limit: int = 100,
    ) -> list:
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
