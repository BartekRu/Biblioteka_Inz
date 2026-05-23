"""
Recommendation Helpers Module
==============================

Helper functions extracted from recommendations.py.
"""

from typing import Optional
from bson import ObjectId
import logging

from ..utils.book_contract import enrich_book_contract

logger = logging.getLogger(__name__)


def normalize_book(book: dict) -> dict:
    """Normalize book fields used by API responses and recommendation code."""
    if not book:
        return book

    book = enrich_book_contract(book)

    if "averageRating" not in book and "average_rating" in book:
        book["averageRating"] = book["average_rating"]

    if "reviewCount" not in book and "total_reviews" in book:
        book["reviewCount"] = book["total_reviews"]

    if "available" not in book and "available_copies" in book:
        book["available"] = book["available_copies"] > 0

    return book


def serialize_doc(doc: dict) -> dict:
    """Convert ObjectId fields to strings."""
    if doc is None:
        return None

    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    if "user_id" in doc and isinstance(doc["user_id"], ObjectId):
        doc["user_id"] = str(doc["user_id"])
    if "book_id" in doc and isinstance(doc["book_id"], ObjectId):
        doc["book_id"] = str(doc["book_id"])

    return doc


async def enrich_recommendations_with_metadata(
    recommendations: list, db, limit: Optional[int] = None
) -> list:
    """
    Enrich LightGCN/content-based recommendation rows with MongoDB book metadata.

    Accepts either raw goodbooks IDs or dict rows containing goodbooks_id, book_id,
    and score. Scores are preserved for MMR instead of being replaced with a
    rank-only placeholder.
    """
    rec_items = []
    for rank, item in enumerate(recommendations or []):
        if isinstance(item, dict):
            rec_items.append(
                {
                    "goodbooks_id": item.get("goodbooks_id") or item.get("goodbooks_book_id"),
                    "book_id": item.get("book_id") or item.get("_id"),
                    "score": item.get("score"),
                    "reason": item.get("reason"),
                    "rank": rank,
                }
            )
        else:
            rec_items.append(
                {
                    "goodbooks_id": item,
                    "book_id": None,
                    "score": None,
                    "reason": None,
                    "rank": rank,
                }
            )

    if limit:
        rec_items = rec_items[:limit]

    goodbooks_ids = []
    goodbooks_ids_as_strings = []
    mongo_ids = []

    for item in rec_items:
        gb_id = item.get("goodbooks_id")
        if gb_id is not None:
            try:
                gb_id_int = int(gb_id)
                goodbooks_ids.append(gb_id_int)
                goodbooks_ids_as_strings.append(str(gb_id_int))
            except (TypeError, ValueError):
                goodbooks_ids_as_strings.append(str(gb_id))

        book_id = item.get("book_id")
        if isinstance(book_id, ObjectId):
            mongo_ids.append(book_id)
        elif isinstance(book_id, str) and ObjectId.is_valid(book_id):
            mongo_ids.append(ObjectId(book_id))

    query_parts = []
    if goodbooks_ids:
        query_parts.append({"goodbooks_book_id": {"$in": goodbooks_ids}})
    if goodbooks_ids_as_strings:
        query_parts.append({"goodbooks_book_id": {"$in": goodbooks_ids_as_strings}})
    if mongo_ids:
        query_parts.append({"_id": {"$in": mongo_ids}})

    if not query_parts:
        return []

    books = await db.books.find({"$or": query_parts}).to_list(length=max(len(rec_items) * 2, 1))
    by_goodbooks_id = {}
    by_mongo_id = {}

    for raw_book in books:
        by_mongo_id[str(raw_book["_id"])] = raw_book
        if raw_book.get("goodbooks_book_id") is not None:
            by_goodbooks_id[str(raw_book["goodbooks_book_id"])] = raw_book

    enriched = []
    seen = set()

    for item in rec_items:
        if limit and len(enriched) >= limit:
            break

        book = None
        gb_id = item.get("goodbooks_id")
        book_id = item.get("book_id")

        if gb_id is not None:
            book = by_goodbooks_id.get(str(gb_id))
            if not book:
                try:
                    book = by_goodbooks_id.get(str(int(gb_id)))
                except (TypeError, ValueError):
                    pass

        if not book and book_id:
            book = by_mongo_id.get(str(book_id))

        if not book:
            continue

        mongo_id = str(book["_id"])
        if mongo_id in seen:
            continue
        seen.add(mongo_id)

        book_data = normalize_book(serialize_doc(book))

        rank_score = 1.0 - (item["rank"] / max(len(rec_items), 1))
        score = item.get("score")
        book_data["score"] = float(score) if score is not None else rank_score
        book_data["lightgcn_score"] = book_data["score"]

        if item.get("reason"):
            book_data["recommendationReason"] = item["reason"]

        enriched.append(book_data)

    return enriched


def calculate_content_similarity(book: dict, user_profile: dict) -> float:
    """Calculate simple content-based similarity."""
    score = 0.0

    if "genres" in book and user_profile.get("favorite_genres"):
        user_genres = {g["genre"] for g in user_profile["favorite_genres"]}
        book_genres = set(book.get("genres", []))

        if user_genres and book_genres:
            overlap = len(user_genres & book_genres)
            genre_score = overlap / len(user_genres)
            score += genre_score * 0.6

    if "author" in book and user_profile.get("favorite_authors"):
        user_authors = {a["author"] for a in user_profile["favorite_authors"]}
        if book["author"] in user_authors:
            score += 0.4

    return min(score, 1.0)


def ensure_object_id(value):
    """Convert valid string IDs to ObjectId, otherwise return the original value."""
    if isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value)
    return value


def ensure_string(value) -> str:
    """Convert ObjectId to string for API responses."""
    if isinstance(value, ObjectId):
        return str(value)
    return value
