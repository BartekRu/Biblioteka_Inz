"""
Recommendation Helpers Module
==============================

Helper functions extracted from recommendations.py
"""

from typing import List, Optional
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


def normalize_book(book: dict) -> dict:
    """Ujednolica nazwy pól w dokumentach książek"""
    if not book:
        return book

    if "genres" not in book:
        if isinstance(book.get("genre"), list):
            book["genres"] = book["genre"]
        elif isinstance(book.get("genre"), str):
            book["genres"] = [book["genre"]]
        else:
            book["genres"] = []

    if "averageRating" not in book and "average_rating" in book:
        book["averageRating"] = book["average_rating"]

    if "reviewCount" not in book and "total_reviews" in book:
        book["reviewCount"] = book["total_reviews"]

    if "available" not in book and "available_copies" in book:
        book["available"] = book["available_copies"] > 0

    return book


def serialize_doc(doc: dict) -> dict:
    """Konwertuje ObjectId na stringi"""
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
    goodbooks_ids: list, db, limit: Optional[int] = None
) -> list:
    """
    Wzbogaca listę goodbooks_book_id o pełne dane z MongoDB.
    Zwraca listę dict z polami potrzebnymi dla MMR (authors, genre, _id, etc.)
    """
    enriched = []
    seen = set()

    for gb_id in goodbooks_ids:
        if limit and len(enriched) >= limit:
            break

        if gb_id in seen:
            continue
        seen.add(gb_id)

        # Znajdź książkę w MongoDB
        book = await db.books.find_one({"goodbooks_book_id": gb_id})
        if not book:
            book = await db.books.find_one({"goodbooks_book_id": str(gb_id)})

        if not book:
            continue

        # Normalizuj i serializuj
        book_data = normalize_book(serialize_doc(book))

        # Dodaj score (placeholder - będzie nadpisany przez MMR)
        book_data["score"] = 1.0 - (len(enriched) / max(len(goodbooks_ids), 1))

        enriched.append(book_data)

    return enriched


def calculate_content_similarity(book: dict, user_profile: dict) -> float:
    """Oblicza podobieństwo content-based"""
    score = 0.0

    # Genre match (60%)
    if "genres" in book and user_profile.get("favorite_genres"):
        user_genres = {g["genre"] for g in user_profile["favorite_genres"]}
        book_genres = set(book.get("genres", []))

        if user_genres and book_genres:
            overlap = len(user_genres & book_genres)
            genre_score = overlap / len(user_genres)
            score += genre_score * 0.6

    # Author familiarity (40%)
    if "author" in book and user_profile.get("favorite_authors"):
        user_authors = {a["author"] for a in user_profile["favorite_authors"]}
        if book["author"] in user_authors:
            score += 0.4

    return min(score, 1.0)


# ==========================================================
#  ID CONVERSION HELPERS
# ==========================================================


def ensure_object_id(value) -> ObjectId:
    """
    Konwertuje string lub ObjectId na ObjectId

    MongoDB queries wymagają ObjectId, ale czasem mamy stringi.
    """
    if isinstance(value, str):
        return ObjectId(value)
    return value


def ensure_string(value) -> str:
    """
    Konwertuje ObjectId lub string na string

    API responses wymagają stringów, ale MongoDB zwraca ObjectId.
    """
    if isinstance(value, ObjectId):
        return str(value)
    return value
