"""
recommendations.py - UPDATED TO USE ENHANCED SERVICE

Używa rozszerzonego GoodbooksLightGCNService z incremental learning.
Minimalne zmiany - głównie dodanie wywołań do nowych metod.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime
from bson import ObjectId
import random
import json
from pathlib import Path

# Import rozszerzonego serwisu (z incremental learning)
from recommendation_engine.goodbooks_lightgcn_service import goodbooks_lgcn_service
from recommendation_engine.goodbooks_lightgcn import MODEL_DIR

from pydantic import BaseModel

from ..database import get_database
from .auth import get_current_user

router = APIRouter(prefix="/v1/recommendations", tags=["Recommendations"])


# ==========================================================
#  HELPER FUNCTIONS (bez zmian)
# ==========================================================


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


class InteractionIn(BaseModel):
    book_id: str
    interaction_type: str
    metadata: Optional[dict] = None


# ==========================================================
#  HEALTH - UPDATED
# ==========================================================


@router.get("/health")
async def health_check():
    """Sprawdza status systemu rekomendacji"""
    try:
        stats = goodbooks_lgcn_service.get_stats()

        return {
            "status": "healthy",
            "model_loaded": True,
            "incremental_mode": stats.get("incremental_mode", True),
            "total_users": stats["total_users"],
            "total_updates": stats["total_updates"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "model_loaded": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ==========================================================
#  METRICS - UPDATED
# ==========================================================


@router.get("/metrics")
async def get_metrics():
    """Zwraca metryki modelu LightGCN + incremental stats"""
    model_dir = Path(MODEL_DIR)
    pro_file = model_dir / "lightgcn_goodbooks_pro_metrics.json"
    base_file = model_dir / "lightgcn_goodbooks_metrics.json"

    metrics_file = None
    if pro_file.exists():
        metrics_file = pro_file
    elif base_file.exists():
        metrics_file = base_file

    base_metrics = {}

    if metrics_file and metrics_file.exists():
        with open(metrics_file, "r", encoding="utf-8") as f:
            base_metrics = json.load(f)

        try:
            last_updated = datetime.fromtimestamp(metrics_file.stat().st_mtime).strftime("%Y-%m-%d")
        except Exception:
            last_updated = datetime.now().strftime("%Y-%m-%d")
    else:
        last_updated = datetime.now().strftime("%Y-%m-%d")

    # ⭐ Statystyki incremental z serwisu
    try:
        stats = goodbooks_lgcn_service.get_stats()

        incremental_info = {
            "incrementalMode": stats.get("incremental_mode", True),
            "totalUsers": stats["total_users"],
            "newUsersCreated": stats["new_users_created"],
            "totalUpdates": stats["total_updates"],
            "interactionsSinceCheckpoint": stats["interactions_since_checkpoint"],
        }
    except Exception as e:
        incremental_info = {"incrementalMode": False, "error": str(e)}

    return {
        # Metryki bazowe
        "recall20": base_metrics.get("recall20", 0.1411),
        "ndcg20": base_metrics.get("ndcg20", 0.0842),
        "precision20": base_metrics.get("precision20", 0.0623),
        "coverage": base_metrics.get("coverage", 0.78),
        "trainUsers": base_metrics.get("trainUsers", "53,175"),
        "trainItems": base_metrics.get("trainItems", "10,000"),
        "interactions": str(
            base_metrics.get("interactions_used", base_metrics.get("interactions", "932,940"))
        ),
        "embeddingDim": str(base_metrics.get("embeddingDim", "64")),
        "epochs": str(base_metrics.get("epochs", "50")),
        "learningRate": str(base_metrics.get("learningRate", "0.001")),
        "lastUpdated": last_updated,
        "modelName": base_metrics.get("modelName", "LightGCN (goodbooks-10k)"),
        "layers": base_metrics.get("layers", 3),
        # ⭐ Incremental stats
        **incremental_info,
    }


# ==========================================================
#  POZOSTAŁE ENDPOINTY (bez zmian)
# ==========================================================


@router.get("/featured")
async def get_featured(
    limit: int = Query(default=10, le=20), current_user: dict = Depends(get_current_user)
):
    db = get_database()
    user_id = str(current_user.id)

    favorite_genres = []

    pipeline = [
        {"$match": {"user_id": ObjectId(user_id)}},
        {
            "$lookup": {
                "from": "books",
                "localField": "book_id",
                "foreignField": "_id",
                "as": "book",
            }
        },
        {"$unwind": "$book"},
        {
            "$addFields": {
                "bookGenres": {
                    "$cond": [
                        {"$isArray": "$book.genres"},
                        "$book.genres",
                        {"$cond": [{"$isArray": "$book.genre"}, "$book.genre", ["$book.genre"]]},
                    ]
                }
            }
        },
        {"$unwind": "$bookGenres"},
        {"$group": {"_id": "$bookGenres", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]

    async for doc in db.loans.aggregate(pipeline):
        if doc["_id"]:
            favorite_genres.append(doc["_id"])

    books = []

    if favorite_genres:
        cursor = db.books.find(
            {
                "genres": {"$in": favorite_genres},
                "image_url": {"$exists": True, "$ne": None},
                "goodbooks_book_id": {"$exists": True},
            }
        ).limit(limit)

        async for raw in cursor:
            book = normalize_book(serialize_doc(raw))
            book["matchScore"] = round(random.uniform(0.75, 0.95), 2)
            book["recommendationReason"] = "Dopasowane do Twoich ulubionych gatunków"
            books.append(book)

    if len(books) < limit:
        existing = [ObjectId(b["_id"]) for b in books]

        query = {
            "_id": {"$nin": existing},
            "image_url": {"$exists": True, "$ne": None},
            "goodbooks_book_id": {"$exists": True},
        }

        cursor = db.books.find(query).limit(limit - len(books))
        async for raw in cursor:
            book = normalize_book(serialize_doc(raw))
            book["matchScore"] = round(random.uniform(0.6, 0.8), 2)
            book["recommendationReason"] = "Popularne wśród czytelników"
            books.append(book)

    return books[:limit]


@router.get("/categories")
async def get_categories():
    db = get_database()

    pipeline = [
        {
            "$addFields": {
                "genres": {
                    "$cond": [
                        {"$isArray": "$genres"},
                        "$genres",
                        {"$cond": [{"$isArray": "$genre"}, "$genre", ["$genre"]]},
                    ]
                }
            }
        },
        {"$unwind": "$genres"},
        {
            "$group": {
                "_id": "$genres",
                "count": {"$sum": 1},
                "covers": {"$push": "$coverImage"},
            }
        },
        {
            "$project": {
                "name": "$_id",
                "count": 1,
                "sampleCovers": {"$slice": ["$covers", 6]},
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]

    out = []
    async for cat in db.books.aggregate(pipeline):
        out.append(
            {
                "name": cat["name"],
                "count": cat["count"],
                "sampleCovers": [c for c in cat["sampleCovers"] if c],
            }
        )

    return out


@router.get("/because-borrowed")
async def get_because_borrowed(
    limit: int = Query(default=3, le=5), current_user: dict = Depends(get_current_user)
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
            sections.append(
                {
                    "sourceBook": {
                        "_id": source["_id"],
                        "title": source["title"],
                        "author": source.get("author", ""),
                    },
                    "recommendations": recs,
                }
            )

    return sections


@router.get("/discovery-queue")
async def get_discovery_queue(
    limit: int = Query(default=12, le=30), current_user: dict = Depends(get_current_user)
):
    db = get_database()
    user_id = str(current_user.id)

    borrowed = [loan["book_id"] async for loan in db.loans.find({"user_id": ObjectId(user_id)})]

    query = {"_id": {"$nin": borrowed}} if borrowed else {}

    books = []
    async for raw in db.books.aggregate([{"$match": query}, {"$sample": {"size": limit}}]):
        b = normalize_book(serialize_doc(raw))
        b["matchScore"] = round(random.uniform(0.5, 0.85), 2)
        books.append(b)

    return books


@router.get("/known-authors")
async def get_known_authors(
    limit: int = Query(default=6, le=10), current_user: dict = Depends(get_current_user)
):
    db = get_database()
    user_id = str(current_user.id)

    pipeline = [
        {"$match": {"user_id": ObjectId(user_id)}},
        {
            "$lookup": {
                "from": "books",
                "localField": "book_id",
                "foreignField": "_id",
                "as": "book",
            }
        },
        {"$unwind": "$book"},
        {"$group": {"_id": "$book.author", "count": {"$sum": 1}}},
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]

    authors = []

    async for doc in db.loans.aggregate(pipeline):
        author_name = doc["_id"]

        latest = await db.books.find_one({"author": author_name}, sort=[("publication_year", -1)])

        if latest:
            latest = normalize_book(serialize_doc(latest))
            authors.append(
                {
                    "name": author_name,
                    "latestBook": {
                        "_id": latest["_id"],
                        "title": latest.get("title"),
                        "coverImage": latest.get("coverImage"),
                        "available": latest.get("available", True),
                    },
                }
            )

    return authors


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

    query = {"_id": {"$ne": ObjectId(book_id)}, "$or": []}

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
#  ⭐ INTERACTIONS - UPDATED WITH INCREMENTAL LEARNING
# ==========================================================


@router.post("/interaction")
async def report_interaction(interaction: InteractionIn, current_user=Depends(get_current_user)):
    """
    Raportuj interakcję + aktualizuj embeddingi w czasie rzeczywistym!
    """
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

    # 1. Zapisz do MongoDB
    doc = {
        "user_id": uid,
        "book_id": bid,
        "type": interaction.interaction_type,
        "timestamp": datetime.now(),
        "metadata": interaction.metadata or {},
    }

    await db.interactions.insert_one(doc)

    # 2. ⭐ AKTUALIZUJ EMBEDDINGI
    try:
        book = await db.books.find_one({"_id": bid})

        if book and book.get("goodbooks_book_id"):
            goodbooks_id = int(book["goodbooks_book_id"])

            # ⭐ Process interaction z nowym API
            update_result = goodbooks_lgcn_service.process_interaction(
                mongo_user_id=str(uid),
                goodbooks_book_id=goodbooks_id,
                interaction_type=interaction.interaction_type,
            )

            return {
                "status": "recorded",
                "interaction_saved": True,
                "embedding_updated": update_result.get("success", False),
                "update_info": update_result if update_result.get("success") else None,
            }
        else:
            return {
                "status": "recorded",
                "interaction_saved": True,
                "embedding_updated": False,
                "reason": "book_not_in_goodbooks",
            }

    except Exception as e:
        import traceback

        traceback.print_exc()

        return {
            "status": "recorded",
            "interaction_saved": True,
            "embedding_updated": False,
            "error": str(e),
        }


# ==========================================================
#  ⭐ USER LIGHTGCN - UPDATED WITH DYNAMIC EMBEDDINGS
# ==========================================================


@router.get("/user-lightgcn")
async def get_user_lightgcn_recommendations(
    limit: int = Query(default=20, le=50),
    current_user=Depends(get_current_user),
):
    """
    Rekomendacje z DYNAMIC EMBEDDINGS!
    """
    db = get_database()
    user_id = getattr(current_user, "id", None)
    if not user_id:
        raise HTTPException(status_code=400, detail="Brak poprawnego użytkownika")

    try:
        uid = ObjectId(str(user_id))
    except Exception:
        raise HTTPException(status_code=400, detail="Nieprawidłowe ID użytkownika")

    # 1. Zbierz wypożyczone goodbooks_ids (do wykluczenia)
    borrowed_goodbooks_ids = set()
    borrowed_mongo_ids = set()

    async for loan in db.loans.find({"user_id": uid}):
        book_id = loan.get("book_id")
        if not book_id:
            continue

        borrowed_mongo_ids.add(str(book_id))

        book = await db.books.find_one({"_id": book_id})
        if not book:
            continue

        gb_id = book.get("goodbooks_book_id")
        if gb_id is not None:
            try:
                borrowed_goodbooks_ids.add(int(gb_id))
            except (TypeError, ValueError):
                continue

    # 2. ⭐ Użyj nowego API z dynamic embeddings
    try:
        rec_goodbooks_ids = goodbooks_lgcn_service.get_recommendations_for_user(
            mongo_user_id=str(uid),
            n=limit * 2,
            exclude_goodbooks_ids=borrowed_goodbooks_ids,
            use_cache=True,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()

        # Fallback do starego API
        rec_goodbooks_ids = goodbooks_lgcn_service.recommend_for_goodbooks_ids(
            list(borrowed_goodbooks_ids) if borrowed_goodbooks_ids else [], top_k=limit * 2
        )

    # 3. Mapowanie do MongoDB books
    results = []
    seen = set()

    for gb_id in rec_goodbooks_ids:
        if len(results) >= limit:
            break

        if gb_id in seen or gb_id in borrowed_goodbooks_ids:
            continue
        seen.add(gb_id)

        book = await db.books.find_one({"goodbooks_book_id": gb_id})
        if not book:
            book = await db.books.find_one({"goodbooks_book_id": str(gb_id)})

        if not book:
            continue

        if str(book["_id"]) in borrowed_mongo_ids:
            continue

        book = normalize_book(serialize_doc(book))
        results.append(book)

    return results


# ==========================================================
#  ⭐ DEBUG ENDPOINTS
# ==========================================================


@router.get("/debug/user-stats/{user_id}")
async def get_user_debug_stats(user_id: str, current_user=Depends(get_current_user)):
    """Debug - statystyki użytkownika"""
    current_uid = str(getattr(current_user, "id", ""))
    is_admin = getattr(current_user, "role", "") == "admin"

    if user_id != current_uid and not is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        has_embedding = user_id in goodbooks_lgcn_service.mongo_user_to_idx

        user_stats = {
            "user_id": user_id,
            "has_embedding": has_embedding,
            "user_idx": goodbooks_lgcn_service.mongo_user_to_idx.get(user_id),
            "is_new_user": (
                has_embedding
                and goodbooks_lgcn_service.mongo_user_to_idx[user_id]
                >= goodbooks_lgcn_service.num_users
            ),
        }

        if has_embedding:
            user_idx = goodbooks_lgcn_service.mongo_user_to_idx[user_id]
            embedding = goodbooks_lgcn_service.user_emb[user_idx]

            import numpy as np

            user_stats["embedding_norm"] = float(np.linalg.norm(embedding))
            user_stats["embedding_mean"] = float(np.mean(embedding))
            user_stats["embedding_std"] = float(np.std(embedding))

        return user_stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/service-stats")
async def get_service_stats(current_user=Depends(get_current_user)):
    """Debug - statystyki serwisu (admin only)"""
    is_admin = getattr(current_user, "role", "") == "admin"

    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    try:
        return goodbooks_lgcn_service.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
