"""
User Analysis Module
====================

Functions for analyzing user preferences
Extracted from recommendations.py
"""

from typing import List
from collections import defaultdict
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


async def get_user_top_genres(db, user_id: str, limit: int = 3) -> List[dict]:
    """Analizuje preferencje gatunkowe użytkownika"""
    interactions = await db.interactions.find(
        {"user_id": user_id, "interaction_type": {"$in": ["borrow", "review", "view"]}}
    ).to_list(length=None)

    if not interactions:
        # Fallback: popularne gatunki
        popular_genres = await db.books.aggregate(
            [
                {
                    "$addFields": {
                        "genre_values": {
                            "$cond": [
                                {"$isArray": "$genres"},
                                "$genres",
                                {
                                    "$cond": [
                                        {"$isArray": "$genre"},
                                        "$genre",
                                        {
                                            "$cond": [
                                                {"$ne": ["$genre", None]},
                                                ["$genre"],
                                                [],
                                            ]
                                        },
                                    ]
                                },
                            ]
                        }
                    }
                },
                {"$unwind": "$genre_values"},
                {"$group": {"_id": "$genre_values", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": limit},
            ]
        ).to_list(length=None)

        return [{"genre": g["_id"], "score": 1.0 - (i * 0.1)} for i, g in enumerate(popular_genres)]

    # ✅ FIX: Konwertuj book_id (string) na ObjectId
    book_ids = [
        ObjectId(i["book_id"]) if isinstance(i["book_id"], str) else i["book_id"]
        for i in interactions
    ]
    books = await db.books.find({"_id": {"$in": book_ids}}).to_list(length=None)

    genre_weights = defaultdict(float)
    interaction_weights = {"borrow": 1.0, "review": 0.8, "view": 0.3}

    for interaction in interactions:
        # ✅ FIX: Konwertuj dla porównania
        book_id_obj = (
            ObjectId(interaction["book_id"])
            if isinstance(interaction["book_id"], str)
            else interaction["book_id"]
        )
        book = next((b for b in books if b["_id"] == book_id_obj), None)
        if not book:
            continue

        # Obsłuż zarówno "genre" jak i "genres"
        book_genres = []
        if "genres" in book and book["genres"]:
            book_genres = book["genres"] if isinstance(book["genres"], list) else [book["genres"]]
        elif "genre" in book and book["genre"]:
            book_genres = book["genre"] if isinstance(book["genre"], list) else [book["genre"]]

        if not book_genres:
            continue

        weight = interaction_weights.get(interaction["interaction_type"], 0.5)
        for genre in book_genres:
            if genre:
                genre_weights[genre] += weight

    # Normalizuj
    max_weight = max(genre_weights.values()) if genre_weights else 1.0
    genre_scores = [
        {"genre": genre, "score": weight / max_weight} for genre, weight in genre_weights.items()
    ]
    genre_scores.sort(key=lambda x: x["score"], reverse=True)

    return genre_scores[:limit]


async def get_user_favorite_authors(db, user_id: str, limit: int = 3) -> List[dict]:
    """Znajduje ulubionych autorów użytkownika"""
    interactions = await db.interactions.find(
        {"user_id": user_id, "interaction_type": {"$in": ["borrow", "review"]}}
    ).to_list(length=None)

    if not interactions:
        return []

    # ✅ FIX: Konwertuj book_id (string) na ObjectId
    book_ids = [
        ObjectId(i["book_id"]) if isinstance(i["book_id"], str) else i["book_id"]
        for i in interactions
    ]
    books = await db.books.find({"_id": {"$in": book_ids}}).to_list(length=None)

    author_weights = defaultdict(float)
    interaction_weights = {"borrow": 1.0, "review": 0.8}

    for interaction in interactions:
        # ✅ FIX: Konwertuj dla porównania
        book_id_obj = (
            ObjectId(interaction["book_id"])
            if isinstance(interaction["book_id"], str)
            else interaction["book_id"]
        )
        book = next((b for b in books if b["_id"] == book_id_obj), None)
        if not book or "author" not in book:
            continue

        weight = interaction_weights.get(interaction["interaction_type"], 0.5)
        author_weights[book["author"]] += weight

    max_weight = max(author_weights.values()) if author_weights else 1.0
    author_scores = [
        {"author": author, "score": weight / max_weight}
        for author, weight in author_weights.items()
    ]
    author_scores.sort(key=lambda x: x["score"], reverse=True)

    return author_scores[:limit]
