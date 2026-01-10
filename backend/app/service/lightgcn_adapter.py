import logging
from typing import Optional
from bson import ObjectId

logger = logging.getLogger(__name__)


class LightGCNAdapter:

    def __init__(self, lightgcn_service, db):

        self.lightgcn = lightgcn_service
        self.db = db

        self._goodbooks_cache = {}
        self._mongo_id_cache = {}

        logger.info("✅ LightGCNAdapter initialized with bidirectional cache")

    async def update_user_embedding_incremental(
        self, user_id: str, book_id: str, interaction_weight: float
    ):

        try:
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

            interaction_type = self._weight_to_type(interaction_weight)

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

        if mongo_book_id in self._goodbooks_cache:
            return self._goodbooks_cache[mongo_book_id]

        try:
            book_key = (
                ObjectId(mongo_book_id) if ObjectId.is_valid(mongo_book_id) else mongo_book_id
            )

            book = await self.db.books.find_one({"_id": book_key}, {"goodbooks_book_id": 1})

            if not book:
                logger.warning(f"⚠️  Book {mongo_book_id} not found in database")
                return None

            goodbooks_id = book.get("goodbooks_book_id")

            if goodbooks_id is None:
                logger.warning(f"⚠️  Book {mongo_book_id} has no goodbooks_book_id field")
                return None

            try:
                goodbooks_id = int(goodbooks_id)
            except (TypeError, ValueError):
                logger.warning(f"⚠️  Invalid goodbooks_book_id for {mongo_book_id}: {goodbooks_id}")
                return None

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

        if goodbooks_id in self._mongo_id_cache:
            return self._mongo_id_cache[goodbooks_id]

        try:
            book = await self.db.books.find_one({"goodbooks_book_id": goodbooks_id}, {"_id": 1})

            if not book:
                logger.debug(f"⚠️  No MongoDB book found for goodbooks_id={goodbooks_id}")
                return None

            mongo_id = str(book["_id"])

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

        if weight >= 0.95:
            return "borrow"
        elif weight >= 0.7:
            return "review"
        elif weight >= 0.25:
            return "view"
        else:
            return "view"

    def get_cache_stats(self) -> dict:

        return {
            "goodbooks_cache_size": len(self._goodbooks_cache),
            "mongo_cache_size": len(self._mongo_id_cache),
            "total_cached_books": len(
                set(self._goodbooks_cache.keys()) | set(self._mongo_id_cache.values())
            ),
        }

    def clear_cache(self):

        self._goodbooks_cache.clear()
        self._mongo_id_cache.clear()
        logger.info("🗑️  LightGCNAdapter cache cleared")
