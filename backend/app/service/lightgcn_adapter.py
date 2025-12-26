"""
services/lightgcn_adapter.py - FIXED VERSION
Adapter connecting InteractionService with GoodbooksLightGCNService
Handles MongoDB book_id <-> goodbooks_book_id conversion

🆕 FIXED: Added bidirectional cache for better performance
"""

import logging
from typing import Optional
from bson import ObjectId

logger = logging.getLogger(__name__)


class LightGCNAdapter:
    """
    Adapter for GoodbooksLightGCNService to use in InteractionService

    Solves the problem:
    - InteractionService works with MongoDB book_id (ObjectId string)
    - GoodbooksLightGCNService requires goodbooks_book_id (int)

    🆕 FIXED: Now has bidirectional cache for better performance
    """

    def __init__(self, lightgcn_service, db):
        """
        Args:
            lightgcn_service: Instance of GoodbooksLightGCNService
            db: MongoDB database handle
        """
        self.lightgcn = lightgcn_service
        self.db = db

        # 🆕 FIXED: Bidirectional cache
        self._goodbooks_cache = {}  # Cache: mongo_id (str) -> goodbooks_id (int)
        self._mongo_id_cache = {}  # 🆕 Cache: goodbooks_id (int) -> mongo_id (str)

        logger.info("✅ LightGCNAdapter initialized with bidirectional cache")

    async def update_user_embedding_incremental(
        self, user_id: str, book_id: str, interaction_weight: float
    ):
        """
        Update user embedding after new interaction

        Args:
            user_id: MongoDB user_id (ObjectId string)
            book_id: MongoDB book_id (ObjectId string)
            interaction_weight: Interaction weight (0.3, 0.8, 1.0)

        Returns:
            Dict with update results
        """
        try:
            # 1. Convert book_id -> goodbooks_book_id
            goodbooks_id = await self._get_goodbooks_id(book_id)

            if goodbooks_id is None:
                logger.warning(
                    f"⚠️  Book {book_id} doesn't have goodbooks_book_id - skipping embedding update"
                )
                return {
                    "success": False,
                    "reason": "book_not_in_goodbooks_dataset",
                    "book_id": book_id,
                }

            # 2. Map interaction_weight -> interaction_type
            # (GoodbooksLightGCNService uses type instead of weight)
            interaction_type = self._weight_to_type(interaction_weight)

            # 3. Call GoodbooksLightGCNService
            result = self.lightgcn.process_interaction(
                mongo_user_id=user_id,
                goodbooks_book_id=goodbooks_id,
                interaction_type=interaction_type,
            )

            if result.get("success"):
                logger.info(
                    f"✅ Embedding updated: user={user_id[:12]}... "
                    f"book={book_id[:12]}... (goodbooks_id={goodbooks_id}) "
                    f"type={interaction_type}"
                )

            return result

        except Exception as e:
            logger.error(f"❌ Embedding update failed: user={user_id}, book={book_id}, error={e}")
            return {"success": False, "reason": "exception", "error": str(e)}

    async def _get_goodbooks_id(self, mongo_book_id: str) -> Optional[int]:
        """
        Get goodbooks_book_id from MongoDB for given book
        Uses cache to minimize DB queries

        🆕 FIXED: Also populates reverse cache (goodbooks_id -> mongo_id)
        """
        # Check cache
        if mongo_book_id in self._goodbooks_cache:
            return self._goodbooks_cache[mongo_book_id]

        try:
            # Convert string -> ObjectId
            book_key = (
                ObjectId(mongo_book_id) if ObjectId.is_valid(mongo_book_id) else mongo_book_id
            )

            # Query MongoDB
            book = await self.db.books.find_one({"_id": book_key}, {"goodbooks_book_id": 1})

            if not book:
                logger.warning(f"⚠️  Book {mongo_book_id} not found in database")
                return None

            goodbooks_id = book.get("goodbooks_book_id")

            if goodbooks_id is None:
                logger.warning(f"⚠️  Book {mongo_book_id} has no goodbooks_book_id field")
                return None

            # Convert to int
            try:
                goodbooks_id = int(goodbooks_id)
            except (TypeError, ValueError):
                logger.warning(f"⚠️  Invalid goodbooks_book_id for {mongo_book_id}: {goodbooks_id}")
                return None

            # 🆕 FIXED: Save in BOTH caches
            self._goodbooks_cache[mongo_book_id] = goodbooks_id
            self._mongo_id_cache[goodbooks_id] = mongo_book_id

            logger.debug(
                f"📝 Cached: mongo_id={mongo_book_id[:12]}... <-> goodbooks_id={goodbooks_id}"
            )

            return goodbooks_id

        except Exception as e:
            logger.error(f"❌ Error getting goodbooks_id for {mongo_book_id}: {e}")
            return None

    async def get_mongo_book_id(self, goodbooks_id: int) -> Optional[str]:
        """
        🆕 NEW: Get MongoDB book_id for given goodbooks_id

        Reverse lookup with cache support

        Args:
            goodbooks_id: Goodbooks book ID (int)

        Returns:
            MongoDB book_id (ObjectId string) or None
        """
        # Check reverse cache
        if goodbooks_id in self._mongo_id_cache:
            return self._mongo_id_cache[goodbooks_id]

        try:
            # Query MongoDB
            book = await self.db.books.find_one({"goodbooks_book_id": goodbooks_id}, {"_id": 1})

            if not book:
                logger.debug(f"⚠️  No MongoDB book found for goodbooks_id={goodbooks_id}")
                return None

            mongo_id = str(book["_id"])

            # Save in BOTH caches
            self._mongo_id_cache[goodbooks_id] = mongo_id
            self._goodbooks_cache[mongo_id] = goodbooks_id

            logger.debug(
                f"📝 Cached (reverse): goodbooks_id={goodbooks_id} <-> mongo_id={mongo_id[:12]}..."
            )

            return mongo_id

        except Exception as e:
            logger.error(f"❌ Error getting mongo_id for goodbooks_id={goodbooks_id}: {e}")
            return None

    @staticmethod
    def _weight_to_type(weight: float) -> str:
        """
        Convert interaction weight to type

        Weights in InteractionService:
        - 0.3 = view
        - 0.8 = review
        - 1.0 = borrow
        """
        if weight >= 0.95:  # 1.0
            return "borrow"
        elif weight >= 0.7:  # 0.8
            return "review"
        elif weight >= 0.25:  # 0.3
            return "view"
        else:
            return "view"  # fallback

    def get_cache_stats(self) -> dict:
        """
        🆕 NEW: Get statistics about cache usage

        Useful for monitoring performance
        """
        return {
            "goodbooks_cache_size": len(self._goodbooks_cache),
            "mongo_cache_size": len(self._mongo_id_cache),
            "total_cached_books": len(
                set(self._goodbooks_cache.keys()) | set(self._mongo_id_cache.values())
            ),
        }

    def clear_cache(self):
        """
        🆕 NEW: Clear all caches

        Useful for testing or when data changes
        """
        self._goodbooks_cache.clear()
        self._mongo_id_cache.clear()
        logger.info("🗑️  LightGCNAdapter cache cleared")
