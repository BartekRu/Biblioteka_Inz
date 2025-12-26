"""
services/recommendation_service.py - FIXED v2
Centralized recommendation service using EXISTING GoodbooksLightGCNService methods
"""

from typing import List, Dict, Optional
from datetime import datetime
from bson import ObjectId
import logging
import numpy as np

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Główny serwis rekomendacji łączący:
    - GoodbooksLightGCNService (model ML) - używa ISTNIEJĄCYCH metod!
    - LightGCNAdapter (konwersja MongoDB <-> Goodbooks)
    - MongoDB (persystencja i dane książek)

    🆕 FIXED v2: Używa get_recommendations_for_user() zamiast bezpośredniego dostępu do embeddingów
    """

    def __init__(
        self,
        lightgcn_service,  # GoodbooksLightGCNService
        lightgcn_adapter,  # LightGCNAdapter
        db,  # MongoDB database
    ):
        self.lightgcn = lightgcn_service
        self.adapter = lightgcn_adapter
        self.db = db

        # Check if model is loaded
        self.is_loaded = (
            hasattr(lightgcn_service, "user_emb") and lightgcn_service.user_emb is not None
        )

        if not self.is_loaded:
            logger.warning(
                "⚠️  GoodbooksLightGCNService not fully loaded - recommendations may fail"
            )
        else:
            # Use num_users/num_items (Twój serwis używa tej nazwy)
            num_users = getattr(
                lightgcn_service, "num_users", getattr(lightgcn_service, "n_users", 0)
            )
            num_items = getattr(
                lightgcn_service, "num_items", getattr(lightgcn_service, "n_items", 0)
            )
            logger.info(
                f"✅ RecommendationService initialized with {num_users:,} users and {num_items:,} items"
            )

    # =========================================================================
    # MAIN RECOMMENDATION METHODS
    # =========================================================================

    async def get_recommendations(
        self, user_id: str, n: int = 30, exclude_books: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get personalized recommendations for user

        🆕 FIXED v2: Uses existing get_recommendations_for_user() method

        Args:
            user_id: MongoDB user_id (ObjectId string)
            n: Number of recommendations
            exclude_books: List of MongoDB book_ids to exclude

        Returns:
            List of {book_id (MongoDB), goodbooks_id, score} dictionaries
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded - cannot generate recommendations")

        try:
            # 1. Convert exclude_books from MongoDB IDs to Goodbooks IDs
            exclude_goodbooks_ids = set()
            if exclude_books:
                for mongo_id in exclude_books:
                    goodbooks_id = await self.adapter._get_goodbooks_id(mongo_id)
                    if goodbooks_id:
                        exclude_goodbooks_ids.add(goodbooks_id)

            logger.info(
                f"📊 Excluding {len(exclude_goodbooks_ids)} books for user {user_id[:12]}..."
            )

            # 2. Use EXISTING get_recommendations_for_user() method
            # This method already handles user index lookup, embedding calculation, etc.
            try:
                rec_goodbooks_ids = self.lightgcn.get_recommendations_for_user(
                    mongo_user_id=user_id,
                    n=n,
                    exclude_goodbooks_ids=exclude_goodbooks_ids,
                    use_cache=False,
                )
            except Exception as e:
                logger.warning(f"⚠️  get_recommendations_for_user failed: {e}, trying fallback")

                # Fallback: use recommend_for_goodbooks_ids if get_recommendations_for_user fails
                rec_goodbooks_ids = self.lightgcn.recommend_for_goodbooks_ids(
                    list(exclude_goodbooks_ids) if exclude_goodbooks_ids else [], top_k=n
                )

            # 3. Convert goodbooks_ids to MongoDB format with scores
            recommendations = []

            for goodbooks_id in rec_goodbooks_ids:
                # Get MongoDB book_id
                mongo_book_id = await self.adapter.get_mongo_book_id(goodbooks_id)

                if mongo_book_id:
                    recommendations.append(
                        {
                            "book_id": mongo_book_id,  # MongoDB ObjectId (string)
                            "goodbooks_id": goodbooks_id,  # Goodbooks ID (int)
                            "score": 1.0 - (len(recommendations) / n),  # Simple descending score
                        }
                    )

            logger.info(
                f"✅ Generated {len(recommendations)} recommendations for user {user_id[:12]}..."
            )

            return recommendations

        except Exception as e:
            logger.error(
                f"❌ Failed to generate recommendations for user {user_id}: {e}", exc_info=True
            )
            raise

    async def get_content_based_recommendations(self, user_id: str, n: int = 10) -> List[Dict]:
        """
        Content-based recommendations for cold-start users

        Uses:
        - User's preferred genres (from interactions)
        - User's preferred authors (from interactions)
        - Fallback to popular books

        Args:
            user_id: MongoDB user_id
            n: Number of recommendations

        Returns:
            List of {book_id, score, reason} dictionaries
        """
        try:
            # Get user's interactions to determine preferences
            interactions = (
                await self.db.interactions.find({"user_id": user_id})
                .sort("created_at", -1)
                .limit(50)
                .to_list(length=50)
            )

            if not interactions:
                # True cold-start → return popular books
                return await self._get_popular_books(n)

            # Extract interacted book IDs
            interacted_book_ids = [i["book_id"] for i in interactions]

            # Get book details
            books = await self.db.books.find(
                {"_id": {"$in": [self._to_object_id(bid) for bid in interacted_book_ids]}}
            ).to_list(length=len(interacted_book_ids))

            # Count genres and authors
            genre_counts = {}
            author_counts = {}

            for book in books:
                # Genres
                for genre in book.get("genres", []):
                    genre_counts[genre] = genre_counts.get(genre, 0) + 1

                # Authors
                for author in book.get("authors", []):
                    author_counts[author] = author_counts.get(author, 0) + 1

            # Get top preferences
            top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:3]

            logger.info(
                f"📊 User {user_id[:12]}... preferences: genres={[g[0] for g in top_genres]}, authors={[a[0] for a in top_authors]}"
            )

            # Build query for matching books
            query = {"$or": []}

            if top_genres:
                query["$or"].append({"genres": {"$in": [g[0] for g in top_genres]}})

            if top_authors:
                query["$or"].append({"authors": {"$in": [a[0] for a in top_authors]}})

            if not query["$or"]:
                return await self._get_popular_books(n)

            # Exclude already interacted books
            query["_id"] = {"$nin": [self._to_object_id(bid) for bid in interacted_book_ids]}

            # Get matching books
            matching_books = await self.db.books.find(query).limit(n * 2).to_list(length=n * 2)

            # Score based on match quality
            scored = []
            for book in matching_books:
                score = 0.0
                reasons = []

                # Genre match
                for genre in book.get("genres", []):
                    if genre in genre_counts:
                        score += genre_counts[genre] * 0.5
                        reasons.append(f"Genre: {genre}")

                # Author match
                for author in book.get("authors", []):
                    if author in author_counts:
                        score += author_counts[author] * 0.3
                        reasons.append(f"Author: {author}")

                # Rating boost
                score += book.get("average_rating", 0) * 0.2

                scored.append(
                    {
                        "book_id": str(book["_id"]),
                        "score": score,
                        "reason": " | ".join(reasons[:2]) if reasons else "Popular book",
                    }
                )

            # Sort and return top-N
            scored.sort(key=lambda x: x["score"], reverse=True)

            logger.info(
                f"✅ Generated {len(scored[:n])} content-based recommendations for user {user_id[:12]}..."
            )

            return scored[:n]

        except Exception as e:
            logger.error(f"❌ Content-based recommendations failed: {e}", exc_info=True)
            return await self._get_popular_books(n)

    # =========================================================================
    # EMBEDDING MANAGEMENT
    # =========================================================================

    async def update_user_embedding_incremental(
        self, user_id: str, book_id: str, interaction_weight: float
    ) -> Dict:
        """
        Update user embedding in real-time using SGD

        This method is called by InteractionService through LightGCNAdapter

        Args:
            user_id: MongoDB user_id
            book_id: MongoDB book_id
            interaction_weight: Weight (0.3=view, 0.8=review, 1.0=borrow)

        Returns:
            Dict with update result
        """
        # Delegate to adapter which handles MongoDB -> Goodbooks conversion
        return await self.adapter.update_user_embedding_incremental(
            user_id=user_id, book_id=book_id, interaction_weight=interaction_weight
        )

    def _get_or_create_user_index(self, mongo_user_id: str) -> int:
        """
        Get or create user index in model

        This is a wrapper around GoodbooksLightGCNService.get_or_create_user_idx
        """
        if hasattr(self.lightgcn, "get_or_create_user_idx"):
            return self.lightgcn.get_or_create_user_idx(mongo_user_id)
        else:
            logger.warning("⚠️  GoodbooksLightGCNService doesn't have get_or_create_user_idx method")
            return None

    async def get_user_embedding_info(self, user_id: str) -> Dict:
        """
        Get diagnostic info about user's embedding

        Useful for debugging why recommendations aren't changing
        """
        try:
            # Check if user exists in model
            user_idx = None
            if hasattr(self.lightgcn, "mongo_user_to_idx"):
                user_idx = self.lightgcn.mongo_user_to_idx.get(user_id)

            has_model_index = user_idx is not None

            # Get MongoDB embedding document
            user_emb_doc = await self.db.user_embeddings.find_one({"user_id": user_id})
            has_mongodb_embedding = user_emb_doc is not None

            # Get interactions count
            interactions_count = await self.db.interactions.count_documents({"user_id": user_id})

            # Check if cold-start
            is_cold_start = interactions_count < 5

            # Get embedding update stats from interactions
            embeddings_updated_count = await self.db.interactions.count_documents(
                {"user_id": user_id, "embedding_updated": True}
            )

            # Get total users in model
            total_model_users = 0
            if hasattr(self.lightgcn, "mongo_user_to_idx"):
                total_model_users = len(self.lightgcn.mongo_user_to_idx)

            return {
                "user_id": user_id,
                "has_model_index": has_model_index,
                "model_index": user_idx,
                "has_mongodb_embedding": has_mongodb_embedding,
                "embedding_last_updated": (
                    user_emb_doc["last_updated"].isoformat()
                    if user_emb_doc and "last_updated" in user_emb_doc
                    else None
                ),
                "interaction_count_mongodb": (
                    user_emb_doc.get("interaction_count", 0) if user_emb_doc else 0
                ),
                "interaction_count_actual": interactions_count,
                "embeddings_updated_count": embeddings_updated_count,
                "is_cold_start": is_cold_start,
                "total_model_users": total_model_users,
                "recommendation": (
                    "All good!"
                    if has_model_index and interactions_count > 5
                    else "Add more interactions (borrow/review books) to improve recommendations"
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get embedding info: {e}")
            return {"user_id": user_id, "error": str(e)}

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _get_popular_books(self, n: int = 10) -> List[Dict]:
        """Get popular books as fallback for cold-start"""
        try:
            popular = (
                await self.db.books.find({}).sort("average_rating", -1).limit(n).to_list(length=n)
            )

            return [
                {
                    "book_id": str(book["_id"]),
                    "score": book.get("average_rating", 0),
                    "reason": "Popular book",
                }
                for book in popular
            ]
        except Exception as e:
            logger.error(f"Failed to get popular books: {e}")
            return []

    def _to_object_id(self, id_value):
        """Convert string to ObjectId if valid, otherwise return as-is"""
        if isinstance(id_value, str) and ObjectId.is_valid(id_value):
            return ObjectId(id_value)
        return id_value


# ============================================================================
# SINGLETON / FACTORY
# ============================================================================

_recommendation_service_instance = None


def get_recommendation_service() -> Optional[RecommendationService]:
    """Get singleton recommendation service instance"""
    global _recommendation_service_instance
    return _recommendation_service_instance


def initialize_recommendation_service(lightgcn_service, lightgcn_adapter, db):
    """
    Initialize recommendation service singleton

    Should be called during app startup
    """
    global _recommendation_service_instance

    if _recommendation_service_instance is not None:
        logger.warning("RecommendationService already initialized")
        return _recommendation_service_instance

    _recommendation_service_instance = RecommendationService(
        lightgcn_service=lightgcn_service, lightgcn_adapter=lightgcn_adapter, db=db
    )

    logger.info("✅ RecommendationService singleton initialized")

    return _recommendation_service_instance
