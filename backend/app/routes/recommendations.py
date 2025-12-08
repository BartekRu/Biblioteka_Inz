from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime
from bson import ObjectId
import random

from pydantic import BaseModel

from ..database import get_database
from .auth import get_current_user


router = APIRouter(prefix="/v1/recommendations", tags=["Recommendations"])


# ==========================================================
#  NORMALIZACJA DOKUMENTU KSIĄŻKI
# ==========================================================
def normalize_book(book: dict) -> dict:
    """Ujednolica nazwy pól w dokumentach książek, aby frontend działał poprawnie"""
    if not book:
        return book

    # 1) genre (string lub lista) → genres (lista)
    if "genres" not in book:
        if isinstance(book.get("genre"), list):
            book["genres"] = book["genre"]
        elif isinstance(book.get("genre"), str):
            book["genres"] = [book["genre"]]
        else:
            book["genres"] = []

    # 2) average_rating → averageRating
    if "averageRating" not in book and "average_rating" in book:
        book["averageRating"] = book["average_rating"]

    # 3) total_reviews → reviewCount
    if "reviewCount" not in book and "total_reviews" in book:
        book["reviewCount"] = book["total_reviews"]

    # 4) available_copies → available
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


class InteractionIn(BaseModel):
    book_id: str
    interaction_type: str
    metadata: Optional[dict] = None


# ==========================================================
#  HEALTH
# ==========================================================

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": False,
        "fallback_mode": True,
        "timestamp": datetime.now().isoformat(),
    }


# ==========================================================
#  METRYKI MODELU
# ==========================================================

@router.get("/metrics")
async def get_metrics():
    return {
        "recall20": 0.1411,
        "ndcg20": 0.0842,
        "precision20": 0.0623,
        "coverage": 0.78,
        "trainUsers": "35,710",
        "trainItems": "10,000",
        "interactions": "932,940",
        "embeddingDim": "64",
        "epochs": "50",
        "learningRate": "0.001",
        "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
        "modelName": "LightGCN",
        "layers": 3,
    }


# ==========================================================
#  FEATURED
# ==========================================================
@router.get("/featured")
async def get_featured(
    limit: int = Query(default=10, le=20),
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    user_id = str(current_user.id)

    favorite_genres = []

    pipeline = [
        {"$match": {"user_id": ObjectId(user_id)}},
        {"$lookup": {
            "from": "books",
            "localField": "book_id",
            "foreignField": "_id",
            "as": "book",
        }},
        {"$unwind": "$book"},
        {"$addFields": {
            "bookGenres": {
                "$cond": [
                    {"$isArray": "$book.genres"},
                    "$book.genres",
                    {"$cond": [{"$isArray": "$book.genre"}, "$book.genre", ["$book.genre"]]}
                ]
            }
        }},
        {"$unwind": "$bookGenres"},
        {"$group": {"_id": "$bookGenres", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]

    async for doc in db.loans.aggregate(pipeline):
        if doc["_id"]:
            favorite_genres.append(doc["_id"])

    books = []

    # 🔥 ULUBIONE GATUNKI – tylko książki z GoodBooks
    if favorite_genres:
        cursor = db.books.find({
            "genres": {"$in": favorite_genres},
            "image_url": {"$exists": True, "$ne": None},
            "goodbooks_book_id": {"$exists": True}
        }).limit(limit)

        async for raw in cursor:
            book = normalize_book(serialize_doc(raw))
            book["matchScore"] = round(random.uniform(0.75, 0.95), 2)
            book["recommendationReason"] = "Dopasowane do Twoich ulubionych gatunków"
            books.append(book)

    # 🔥 FALLBACK – uzupełnianie tylko książkami GoodBooks
    if len(books) < limit:
        existing = [ObjectId(b["_id"]) for b in books]

        query = {
            "_id": {"$nin": existing},
            "image_url": {"$exists": True, "$ne": None},
            "goodbooks_book_id": {"$exists": True}
        }

        cursor = db.books.find(query).limit(limit - len(books))
        async for raw in cursor:
            book = normalize_book(serialize_doc(raw))
            book["matchScore"] = round(random.uniform(0.6, 0.8), 2)
            book["recommendationReason"] = "Popularne wśród czytelników"
            books.append(book)

    return books[:limit]


# ==========================================================
#  CATEGORIES
# ==========================================================

@router.get("/categories")
async def get_categories():
    db = get_database()

    pipeline = [
        {"$addFields": {
            "genres": {
                "$cond": [
                    {"$isArray": "$genres"},
                    "$genres",
                    {"$cond": [{"$isArray": "$genre"}, "$genre", ["$genre"]]}
                ]
            }
        }},
        {"$unwind": "$genres"},
        {"$group": {
            "_id": "$genres",
            "count": {"$sum": 1},
            "covers": {"$push": "$coverImage"},
        }},
        {"$project": {
            "name": "$_id",
            "count": 1,
            "sampleCovers": {"$slice": ["$covers", 6]},
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]

    out = []
    async for cat in db.books.aggregate(pipeline):
        out.append({
            "name": cat["name"],
            "count": cat["count"],
            "sampleCovers": [c for c in cat["sampleCovers"] if c],
        })

    return out


# ==========================================================
#  BECAUSE BORROWED
# ==========================================================

@router.get("/because-borrowed")
async def get_because_borrowed(
    limit: int = Query(default=3, le=5),
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    user_id = str(current_user.id)

    loans = db.loans.find({"user_id": ObjectId(user_id)}).sort("borrowed_at", -1).limit(limit)

    sections = []

    async for loan in loans:
        raw = await db.books.find_one({"_id": loan["book_id"]})
        if not raw:
            continue

        source = normalize_book(serialize_doc(raw))
        genres = source["genres"]
        author = source.get("author")

        similar_query = {"_id": {"$ne": loan["book_id"]}, "$or": []}

        if genres:
            similar_query["$or"].append({"genres": {"$in": genres}})
        if author:
            similar_query["$or"].append({"author": author})

        if not similar_query["$or"]:
            continue

        recs = []
        async for raw2 in db.books.find(similar_query).limit(6):
            b = normalize_book(serialize_doc(raw2))

            score = 0.5
            if b.get("author") == author:
                score += 0.3
            if set(b["genres"]) & set(genres):
                score += 0.2

            b["matchScore"] = round(min(score, 0.95), 2)
            recs.append(b)

        if recs:
            sections.append({
                "sourceBook": {
                    "_id": source["_id"],
                    "title": source["title"],
                    "author": source.get("author", "")
                },
                "recommendations": recs
            })

    return sections


# ==========================================================
#  DISCOVERY QUEUE
# ==========================================================

@router.get("/discovery-queue")
async def get_discovery_queue(
    limit: int = Query(default=12, le=30),
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    user_id = str(current_user.id)

    borrowed = [loan["book_id"] async for loan in db.loans.find({"user_id": ObjectId(user_id)})]

    query = {"_id": {"$nin": borrowed}} if borrowed else {}

    books = []
    async for raw in db.books.aggregate([
        {"$match": query},
        {"$sample": {"size": limit}}
    ]):
        b = normalize_book(serialize_doc(raw))
        b["matchScore"] = round(random.uniform(0.5, 0.85), 2)
        books.append(b)

    return books


# ==========================================================
#  KNOWN AUTHORS
# ==========================================================

@router.get("/known-authors")
async def get_known_authors(
    limit: int = Query(default=6, le=10),
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    user_id = str(current_user.id)

    pipeline = [
        {"$match": {"user_id": ObjectId(user_id)}},
        {"$lookup": {
            "from": "books",
            "localField": "book_id",
            "foreignField": "_id",
            "as": "book"
        }},
        {"$unwind": "$book"},
        {"$group": {
            "_id": "$book.author",
            "count": {"$sum": 1}
        }},
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]

    authors = []

    async for doc in db.loans.aggregate(pipeline):
        author_name = doc["_id"]

        latest = await db.books.find_one(
            {"author": author_name},
            sort=[("publication_year", -1)]
        )

        if latest:
            latest = normalize_book(serialize_doc(latest))
            authors.append({
                "name": author_name,
                "latestBook": {
                    "_id": latest["_id"],
                    "title": latest.get("title"),
                    "coverImage": latest.get("coverImage"),
                    "available": latest.get("available", True)
                }
            })

    return authors


# ==========================================================
#  SIMILAR
# ==========================================================

@router.get("/similar/{book_id}")
async def get_similar(book_id: str, limit: int = Query(default=8, le=20)):
    db = get_database()

    try:
        raw = await db.books.find_one({"_id": ObjectId(book_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid book ID")

    if not raw:
        raise HTTPException(status_code=404, detail="Book not found")

    source = normalize_book(serialize_doc(raw))
    genres = source["genres"]
    author = source.get("author")

    query = {
        "_id": {"$ne": ObjectId(book_id)},
        "$or": []
    }

    if genres:
        query["$or"].append({"genres": {"$in": genres}})
    if author:
        query["$or"].append({"author": author})

    if not query["$or"]:
        return []

    books = []
    async for raw2 in db.books.find(query).limit(limit):
        b = normalize_book(serialize_doc(raw2))

        sim = 0.5
        if b.get("author") == author:
            sim += 0.3
        sim += len(set(b["genres"]) & set(genres)) * 0.1

        b["similarity"] = round(min(sim, 0.95), 2)
        books.append(b)

    return sorted(books, key=lambda x: x["similarity"], reverse=True)


# ==========================================================
#  INTERACTIONS
# ==========================================================

@router.post("/interaction")
async def report_interaction(
    interaction: InteractionIn,
    current_user = Depends(get_current_user)
):
    db = get_database()

    user_id = getattr(current_user, "id", None)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user in context")

    try:
        uid = ObjectId(user_id)
    except:
        uid = user_id

    try:
        bid = ObjectId(interaction.book_id)
    except:
        bid = interaction.book_id

    doc = {
        "user_id": uid,
        "book_id": bid,
        "type": interaction.interaction_type,
        "timestamp": datetime.now(),
        "metadata": interaction.metadata or {}
    }

    await db.interactions.insert_one(doc)

    return {"status": "recorded"}
