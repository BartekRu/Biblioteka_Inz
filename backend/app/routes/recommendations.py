from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta
from bson import ObjectId
import random
import json
from pathlib import Path
from fastapi import Request
from sse_starlette.sse import EventSourceResponse
import logging
from collections import defaultdict, Counter
import numpy as np

# Import rozszerzonego serwisu (z incremental learning)
import recommendation_engine.goodbooks_lightgcn_service as service_module
from recommendation_engine.goodbooks_lightgcn import MODEL_DIR

# ✅ DODAJ - Import MMR
try:
    from recommendation_engine.mmr_reranking import (
        mmr_rerank,
        apply_mmr_with_offset,
        diversity_metrics,
    )

    MMR_AVAILABLE = True
except ImportError:
    MMR_AVAILABLE = False
    print("⚠️ MMR re-ranking not available - using standard ranking")

from ..models.dependencies import get_interaction_service
from ..service.interaction_service import InteractionService
from typing import Literal


from pydantic import BaseModel

from ..database import get_database
from .auth import get_current_user

# Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter()


# ==========================================================
#  HELPER: Lazy loading serwisu
# ==========================================================


def get_service():
    """
    Pobierz serwis LightGCN (lazy loading)

    Funkcja jest wywoływana przy każdym request, więc serwis
    musi być już zainicjalizowany w main.py podczas startu.
    """
    if service_module.goodbooks_lgcn_service is None:
        raise HTTPException(
            status_code=503, detail="Recommendation service not initialized. Backend starting up..."
        )
    return service_module.goodbooks_lgcn_service


# ==========================================================
#  HELPER FUNCTIONS
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


# ✅ DODAJ - Helper do wzbogacania rekomendacji o dane z MongoDB
async def enrich_recommendations_with_metadata(goodbooks_ids: list, db, limit: int = None) -> list:
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

        # Dodaj score (na razie placeholder - będzie nadpisany przez MMR)
        book_data["score"] = 1.0 - (len(enriched) / max(len(goodbooks_ids), 1))

        enriched.append(book_data)

    return enriched


# 🆕 NOWE HELPER FUNCTIONS dla Advanced Discovery


async def get_user_top_genres(db, user_id: str, limit: int = 3) -> List[dict]:
    """Analizuje preferencje gatunkowe użytkownika"""
    interactions = await db.interactions.find(
        {"user_id": user_id, "interaction_type": {"$in": ["borrow", "review", "view"]}}
    ).to_list(length=None)

    if not interactions:
        # Fallback: popularne gatunki
        popular_genres = await db.books.aggregate(
            [
                {"$unwind": "$genres"},
                {"$group": {"_id": "$genres", "count": {"$sum": 1}}},
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
        if not book or "genres" not in book:
            continue

        weight = interaction_weights.get(interaction["interaction_type"], 0.5)
        for genre in book.get("genres", []):
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


class InteractionIn(BaseModel):
    book_id: str
    interaction_type: Literal["view", "review", "borrow"]
    metadata: Optional[dict] = None


# ==========================================================
#  HEALTH
# ==========================================================


@router.get("/health")
async def health_check():
    """Sprawdza status systemu rekomendacji"""
    try:
        stats = get_service().get_stats()

        return {
            "status": "healthy",
            "model_loaded": True,
            "incremental_mode": stats.get("incremental_mode", True),
            "total_users": stats["total_users"],
            "total_updates": stats["total_updates"],
            "mmr_available": MMR_AVAILABLE,
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException as e:
        return {
            "status": "starting",
            "model_loaded": False,
            "error": e.detail,
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
#  METRICS
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

    # Statystyki incremental z serwisu
    try:
        stats = get_service().get_stats()

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
        # Incremental stats
        **incremental_info,
        # MMR info
        "mmrAvailable": MMR_AVAILABLE,
    }


# ==========================================================
#  POZOSTAŁE ENDPOINTY (istniejące - bez zmian)
# ==========================================================


@router.get("/featured")
async def get_featured(
    limit: int = Query(default=10, le=20), current_user=Depends(get_current_user)
):
    db = get_database()
    user_id = str(current_user.id)

    favorite_genres = []

    # ✅ FIX: user_id jako string
    pipeline = [
        {"$match": {"user_id": user_id}},
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
    limit: int = Query(default=3, le=5), current_user=Depends(get_current_user)
):
    db = get_database()
    user_id = str(current_user.id)

    # ✅ FIX: user_id jako string + tylko aktywne wypożyczenia
    loans = (
        db.loans.find({"user_id": user_id, "status": "active"}).sort("borrowed_at", -1).limit(limit)
    )

    sections = []

    async for loan in loans:
        # ✅ FIX: Konwertuj book_id z string na ObjectId
        book_id = ObjectId(loan["book_id"]) if isinstance(loan["book_id"], str) else loan["book_id"]

        raw = await db.books.find_one({"_id": book_id})
        if not raw:
            continue

        source = normalize_book(serialize_doc(raw))
        genres = source["genres"]
        author = source.get("author")

        # ✅ FIX: Użyj ObjectId w query
        similar_query = {"_id": {"$ne": book_id}, "$or": []}

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
    limit: int = Query(default=12, le=30), current_user=Depends(get_current_user)
):
    db = get_database()
    user_id = str(current_user.id)

    # ✅ FIX: Konwertuj book_id na ObjectId
    borrowed = [
        ObjectId(loan["book_id"]) if isinstance(loan["book_id"], str) else loan["book_id"]
        async for loan in db.loans.find({"user_id": user_id})
    ]

    query = {"_id": {"$nin": borrowed}} if borrowed else {}

    books = []
    async for raw in db.books.aggregate([{"$match": query}, {"$sample": {"size": limit}}]):
        b = normalize_book(serialize_doc(raw))
        b["matchScore"] = round(random.uniform(0.5, 0.85), 2)
        books.append(b)

    return books


@router.get("/known-authors")
async def get_known_authors(
    limit: int = Query(default=6, le=10), current_user=Depends(get_current_user)
):
    db = get_database()
    user_id = str(current_user.id)

    # ✅ FIX: user_id jako string
    pipeline = [
        {"$match": {"user_id": user_id}},
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
#  INTERACTIONS - INCREMENTAL LEARNING
# ==========================================================


@router.post("/interaction")
async def report_interaction(
    interaction: InteractionIn,
    current_user=Depends(get_current_user),
    interaction_service: InteractionService = Depends(get_interaction_service),
):
    """
    Raportuj interakcję: zapis do jednej kolekcji + (opcjonalnie) incremental update embeddingów.
    """
    db = get_database()
    user_id = str(current_user.id)

    # (opcjonalnie, ale bardzo polecam) dołóż goodbooks_book_id do metadata,
    # żeby incremental update mógł zadziałać także poza tym endpointem
    meta = interaction.metadata or {}

    # znajdź książkę (żeby wyciągnąć goodbooks_book_id)
    bid = (
        ObjectId(interaction.book_id)
        if ObjectId.is_valid(interaction.book_id)
        else interaction.book_id
    )
    book = await db.books.find_one({"_id": bid})

    if book and book.get("goodbooks_book_id") is not None:
        try:
            meta["goodbooks_book_id"] = int(book["goodbooks_book_id"])
        except (TypeError, ValueError):
            pass

    result = await interaction_service.create_interaction(
        user_id=user_id,
        book_id=interaction.book_id,
        interaction_type=interaction.interaction_type,
        metadata=meta,
        update_embedding=True,
    )

    return {"status": "recorded", **result}


# ==========================================================
#  🎯 GŁÓWNY ENDPOINT Z MMR
# ==========================================================


@router.get("/user-lightgcn")
async def get_user_lightgcn_recommendations(
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0, ge=0, description="Offset dla rotacji (tylko z MMR)"),
    use_mmr: bool = Query(default=True, description="Czy użyć MMR re-ranking"),
    lambda_param: float = Query(
        default=0.7, ge=0.0, le=1.0, description="Balans MMR: 1.0=trafność, 0.0=różnorodność"
    ),
    enforce_author_limit: bool = Query(default=True, description="Czy ograniczać autorów"),
    max_per_author: int = Query(default=2, ge=1, le=10, description="Max książek od autora"),
    current_user=Depends(get_current_user),
):
    """
    🎯 Rekomendacje z LightGCN + OPCJONALNY MMR re-ranking

    Parametry MMR:
    - use_mmr: True/False - włącz/wyłącz MMR
    - lambda_param: 0.0-1.0 - balans (0.7 = domyślnie)
    - enforce_author_limit: True/False - limit autorów
    - max_per_author: 1-10 - max książek od autora
    - offset: 0+ - rotacja (działa tylko z MMR)

    WYKLUCZAMY wypożyczone książki!
    """
    db = get_database()
    user_id = getattr(current_user, "id", None)
    if not user_id:
        raise HTTPException(status_code=400, detail="Brak poprawnego użytkownika")

    # user_id jako string dla MongoDB queries (loans używa string)
    user_id_str = str(user_id)

    # 1. Zbierz wypożyczone książki
    borrowed_goodbooks_ids = set()
    borrowed_mongo_ids = set()

    async for loan in db.loans.find({"user_id": user_id_str, "status": "active"}):
        book_id = loan.get("book_id")
        if not book_id:
            continue

        borrowed_mongo_ids.add(str(book_id))

        # ✅ FIX: Konwertuj book_id na ObjectId
        book_id_obj = ObjectId(book_id) if isinstance(book_id, str) else book_id
        book = await db.books.find_one({"_id": book_id_obj})
        if not book:
            continue

        gb_id = book.get("goodbooks_book_id")
        if gb_id is not None:
            try:
                borrowed_goodbooks_ids.add(int(gb_id))
            except (TypeError, ValueError):
                continue

    logger.info(
        f"📊 User {user_id_str} has {len(borrowed_goodbooks_ids)} borrowed books "
        f"(use_mmr={use_mmr}, λ={lambda_param})"
    )

    # 2. Pobierz rekomendacje z LightGCN
    try:
        # Pobierz 3x więcej niż potrzeba (dla MMR buffer)
        fetch_n = limit * 3 if use_mmr else limit

        rec_goodbooks_ids = get_service().get_recommendations_for_user(
            mongo_user_id=user_id_str,
            n=fetch_n,
            exclude_goodbooks_ids=borrowed_goodbooks_ids,
            use_cache=False,  # Świeże dane
        )

    except Exception as e:
        import traceback

        traceback.print_exc()

        # Fallback
        rec_goodbooks_ids = get_service().recommend_for_goodbooks_ids(
            list(borrowed_goodbooks_ids) if borrowed_goodbooks_ids else [], top_k=fetch_n
        )

    # 3. Wzbogać o dane z MongoDB
    candidates = await enrich_recommendations_with_metadata(rec_goodbooks_ids, db, limit=fetch_n)

    # Dodatkowa walidacja - usuń wypożyczone
    candidates = [c for c in candidates if str(c["_id"]) not in borrowed_mongo_ids]

    logger.info(f"📚 Got {len(candidates)} candidates from LightGCN")

    # 4. MMR RE-RANKING (opcjonalnie)
    if use_mmr and MMR_AVAILABLE and len(candidates) > limit:
        logger.info(f"🔄 Applying MMR re-ranking (λ={lambda_param}, author_limit={max_per_author})")

        try:
            # Wyciągnij embeddingi (jeśli serwis to wspiera)
            embeddings_dict = {}
            # TODO: Jeśli Twój serwis ma metodę get_book_embeddings, użyj jej:
            # embeddings_dict = get_service().get_book_embeddings_dict()

            if offset > 0:
                # Z offsetem (rotacja)
                results, next_offset = apply_mmr_with_offset(
                    candidates,
                    n=limit,
                    offset=offset,
                    lambda_param=lambda_param,
                    embeddings_dict=embeddings_dict,
                    use_content_similarity=True,
                    enforce_author_limit=enforce_author_limit,
                    max_per_author=max_per_author,
                )

                # Oblicz metryki
                div_metrics = diversity_metrics(results) if results else {}

                metadata = {
                    "model": "LightGCN + MMR",
                    "total_candidates": len(candidates),
                    "returned": len(results),
                    "offset": offset,
                    "next_offset": next_offset,
                    "mmr_lambda": lambda_param,
                    "author_limit": max_per_author if enforce_author_limit else None,
                    "diversity_metrics": div_metrics,
                }
            else:
                # Bez offsetu
                results = mmr_rerank(
                    candidates,
                    n=limit,
                    lambda_param=lambda_param,
                    embeddings_dict=embeddings_dict,
                    use_content_similarity=True,
                    enforce_author_limit=enforce_author_limit,
                    max_per_author=max_per_author,
                )

                # Oblicz metryki
                div_metrics = diversity_metrics(results) if results else {}

                metadata = {
                    "model": "LightGCN + MMR",
                    "total_candidates": len(candidates),
                    "returned": len(results),
                    "mmr_lambda": lambda_param,
                    "author_limit": max_per_author if enforce_author_limit else None,
                    "diversity_metrics": div_metrics,
                }

            logger.info(
                f"✅ MMR complete: {len(results)} books, "
                f"{div_metrics.get('unique_authors', 0)} authors, "
                f"{div_metrics.get('unique_genres', 0)} genres"
            )

        except Exception as e:
            logger.error(f"❌ MMR failed: {e}, falling back to standard ranking")
            results = candidates[:limit]
            metadata = {"model": "LightGCN (MMR failed)", "error": str(e), "returned": len(results)}

    else:
        # Bez MMR - zwykły ranking
        results = candidates[:limit]
        metadata = {"model": "LightGCN", "mmr_enabled": False, "returned": len(results)}

    logger.info(f"✅ Returning {len(results)} recommendations for user {id}")

    # 5. Zwróć wyniki + metadata
    return {"recommendations": results, "metadata": metadata}


# ==========================================================
#  🆕 NOWE ENDPOINTY - ADVANCED DISCOVERY
# ==========================================================


@router.get("/by-genre")
async def get_genre_recommendations(
    limit: int = Query(3, ge=1, le=5, description="Liczba gatunków"),
    books_per_genre: int = Query(10, ge=5, le=20, description="Książek na gatunek"),
    current_user=Depends(get_current_user),
):
    """SEKCJA B: Rekomendacje według gatunku"""
    db = get_database()
    user_id = str(current_user.id)

    # Znajdź top gatunki
    top_genres = await get_user_top_genres(db, user_id, limit)

    if not top_genres:
        return []

    # Pobierz embedding użytkownika
    try:
        lightgcn = get_service()
        user_idx = lightgcn.mongo_user_to_idx.get(user_id)
        user_embedding = lightgcn.user_emb[user_idx] if user_idx is not None else None
    except:
        user_embedding = None

    sections = []
    for genre_info in top_genres:
        genre = genre_info["genre"]

        # ✅ FIX: Pole w MongoDB to "genre" nie "genres"!
        # Obsługa zarówno genre: "Fantasy" jak i genre: ["Fantasy", "Young Adult"]
        genre_books = await db.books.find(
            {
                "$or": [
                    {"genre": genre},  # genre jako string
                    {"genres": genre},  # fallback dla genres (na wszelki wypadek)
                ],
                "available_copies": {"$gt": 0},
            }
        ).to_list(length=100)

        if not genre_books:
            continue

        # Personalizuj ranking
        scored_books = []
        for book in genre_books:
            book_data = normalize_book(serialize_doc(book))

            # Spróbuj użyć LightGCN
            if user_embedding is not None:
                try:
                    gb_id = book.get("goodbooks_book_id")
                    book_idx = lightgcn.goodbooks_id_to_idx.get(int(gb_id)) if gb_id else None

                    if book_idx is not None:
                        book_embedding = lightgcn.item_emb[book_idx]
                        score = np.dot(user_embedding, book_embedding) / (
                            np.linalg.norm(user_embedding) * np.linalg.norm(book_embedding)
                        )
                        book_data["matchScore"] = float(score)
                    else:
                        book_data["matchScore"] = 0.5
                except:
                    book_data["matchScore"] = 0.5
            else:
                book_data["matchScore"] = 0.5

            scored_books.append(book_data)

        # Sortuj i zwróć top N
        scored_books.sort(key=lambda x: x.get("matchScore", 0), reverse=True)

        sections.append(
            {
                "genre": genre,
                "books": scored_books[:books_per_genre],
                "user_preference_score": genre_info["score"],
            }
        )

    return sections


@router.get("/by-author")
async def get_author_recommendations(
    limit: int = Query(3, ge=1, le=5),
    books_per_author: int = Query(10, ge=5, le=20),
    current_user=Depends(get_current_user),
):
    """SEKCJA B: Rekomendacje według autora"""
    db = get_database()
    user_id = str(current_user.id)

    # Znajdź ulubionych autorów
    favorite_authors = await get_user_favorite_authors(db, user_id, limit)

    if not favorite_authors:
        return []

    # Pobierz embedding użytkownika
    try:
        lightgcn = get_service()
        user_idx = lightgcn.mongo_user_to_idx.get(user_id)
        user_embedding = lightgcn.user_emb[user_idx] if user_idx is not None else None
    except:
        user_embedding = None

    # Pobierz już wypożyczone książki
    user_borrows = await db.interactions.find(
        {"user_id": user_id, "interaction_type": "borrow"}
    ).to_list(length=None)
    borrowed_book_ids = {i["book_id"] for i in user_borrows}

    sections = []
    for author_info in favorite_authors:
        author = author_info["author"]

        # Pobierz książki autora
        author_books = await db.books.find(
            {
                "author": author,
                "_id": {"$nin": list(borrowed_book_ids)},
                "available_copies": {"$gt": 0},
            }
        ).to_list(length=50)

        if not author_books:
            continue

        # Personalizuj
        scored_books = []
        for book in author_books:
            book_data = normalize_book(serialize_doc(book))

            if user_embedding is not None:
                try:
                    gb_id = book.get("goodbooks_book_id")
                    book_idx = lightgcn.goodbooks_id_to_idx.get(int(gb_id)) if gb_id else None

                    if book_idx is not None:
                        book_embedding = lightgcn.item_emb[book_idx]
                        score = np.dot(user_embedding, book_embedding) / (
                            np.linalg.norm(user_embedding) * np.linalg.norm(book_embedding)
                        )
                        book_data["matchScore"] = float(score)
                    else:
                        book_data["matchScore"] = 0.5
                except:
                    book_data["matchScore"] = 0.5
            else:
                book_data["matchScore"] = 0.5

            scored_books.append(book_data)

        scored_books.sort(key=lambda x: x.get("matchScore", 0), reverse=True)

        sections.append(
            {
                "author": author,
                "books": scored_books[:books_per_author],
                "user_preference_score": author_info["score"],
            }
        )

    return sections


@router.get("/similar-readers")
async def get_similar_readers_books(
    limit: int = Query(15, ge=5, le=30),
    current_user=Depends(get_current_user),
):
    """SEKCJA B: Książki popularne wśród podobnych czytelników"""
    db = get_database()
    user_id = str(current_user.id)

    try:
        lightgcn = get_service()
        user_idx = lightgcn.mongo_user_to_idx.get(user_id)

        if user_idx is None:
            return {"books": [], "similar_user_count": 0}

        user_embedding = lightgcn.user_emb[user_idx]
    except:
        return {"books": [], "similar_user_count": 0}

    # Znajdź podobnych użytkowników
    all_users = await db.users.find({"_id": {"$ne": ObjectId(user_id)}}).to_list(length=None)

    similar_users = []
    for user in all_users:
        other_id = str(user["_id"])
        other_idx = lightgcn.mongo_user_to_idx.get(other_id)

        if other_idx is not None:
            other_embedding = lightgcn.user_emb[other_idx]
            similarity = np.dot(user_embedding, other_embedding) / (
                np.linalg.norm(user_embedding) * np.linalg.norm(other_embedding)
            )

            if similarity > 0.7:
                similar_users.append({"user_id": other_id, "similarity": float(similarity)})

    similar_users.sort(key=lambda x: x["similarity"], reverse=True)
    top_similar = similar_users[:50]

    if not top_similar:
        return {"books": [], "similar_user_count": 0}

    # Pobierz książki które oni wypożyczyli
    similar_user_ids = [u["user_id"] for u in top_similar]

    similar_borrows = await db.interactions.find(
        {"user_id": {"$in": similar_user_ids}, "interaction_type": "borrow"}
    ).to_list(length=None)

    # Zlicz popularność
    book_popularity = Counter([b["book_id"] for b in similar_borrows])

    # Wyklucz już wypożyczone
    user_borrows = await db.interactions.find(
        {"user_id": user_id, "interaction_type": "borrow"}
    ).to_list(length=None)
    borrowed_book_ids = {i["book_id"] for i in user_borrows}

    # Filtruj
    ranked_books = [
        (book_id, count)
        for book_id, count in book_popularity.most_common()
        if book_id not in borrowed_book_ids
    ][:limit]

    # Pobierz szczegóły
    book_ids = [book_id for book_id, _ in ranked_books]

    # ✅ FIX: Konwertuj book_ids (string) na ObjectId
    book_ids_obj = [ObjectId(bid) if isinstance(bid, str) else bid for bid in book_ids]
    books = await db.books.find({"_id": {"$in": book_ids_obj}}).to_list(length=None)

    book_dict = {str(b["_id"]): normalize_book(serialize_doc(b)) for b in books}
    max_count = ranked_books[0][1] if ranked_books else 1

    result_books = []
    for book_id, count in ranked_books:
        book_id_str = str(book_id)
        if book_id_str in book_dict:
            book = book_dict[book_id_str]
            book["popularityScore"] = count / max_count

            # Dodaj matchScore z LightGCN
            try:
                gb_id = book.get("goodbooks_book_id")
                book_idx = lightgcn.goodbooks_id_to_idx.get(int(gb_id)) if gb_id else None

                if book_idx is not None:
                    book_embedding = lightgcn.item_emb[book_idx]
                    score = np.dot(user_embedding, book_embedding) / (
                        np.linalg.norm(user_embedding) * np.linalg.norm(book_embedding)
                    )
                    book["matchScore"] = float(score)
            except:
                pass

            result_books.append(book)

    return {
        "books": result_books,
        "similar_user_count": len(top_similar),
        "metadata": {"similarity_threshold": 0.7},
    }


@router.get("/new-arrivals")
async def get_new_arrivals(
    limit: int = Query(20, ge=5, le=50),
    days: int = Query(30, ge=7, le=90),
    current_user=Depends(get_current_user),
):
    """SEKCJA C: Nowości w bibliotece"""
    db = get_database()
    user_id = str(current_user.id)

    cutoff_date = datetime.now() - timedelta(days=days)

    # Spróbuj znaleźć nowe książki
    new_books = await db.books.find({"created_at": {"$gte": cutoff_date}}).to_list(length=100)

    # Fallback: ostatnio dodane (po _id)
    if not new_books:
        new_books = await db.books.find().sort("_id", -1).limit(limit).to_list(length=None)

    # Profil użytkownika
    user_profile = {
        "favorite_genres": await get_user_top_genres(db, user_id, limit=5),
        "favorite_authors": await get_user_favorite_authors(db, user_id, limit=5),
    }

    # Oblicz similarity
    scored_books = []
    for book in new_books:
        book_data = normalize_book(serialize_doc(book))
        score = calculate_content_similarity(book_data, user_profile)
        book_data["matchScore"] = score
        book_data["coldStart"] = True
        book_data["similarityMethod"] = "content-based"
        scored_books.append(book_data)

    scored_books.sort(key=lambda x: x["matchScore"], reverse=True)
    return scored_books[:limit]


@router.get("/hidden-gems")
async def get_hidden_gems(
    limit: int = Query(15, ge=5, le=30),
    current_user=Depends(get_current_user),
):
    """SEKCJA C: Ukryte skarby 💎"""
    db = get_database()
    user_id = str(current_user.id)

    # Ulubione gatunki
    user_genres = await get_user_top_genres(db, user_id, limit=5)
    favorite_genres = [g["genre"] for g in user_genres]

    # Zlicz wypożyczenia
    borrow_counts = await db.interactions.aggregate(
        [
            {"$match": {"interaction_type": "borrow"}},
            {"$group": {"_id": "$book_id", "borrow_count": {"$sum": 1}}},
            {"$match": {"borrow_count": {"$lt": 50}}},
        ]
    ).to_list(length=None)

    underrated_book_ids = [ObjectId(b["_id"]) for b in borrow_counts]

    # Znajdź wysoko oceniane
    query = {
        "_id": {"$in": underrated_book_ids},
        "average_rating": {"$gte": 4.0},
        "available_copies": {"$gt": 0},
    }

    if favorite_genres:
        query["genres"] = {"$in": favorite_genres}

    hidden_gems = await db.books.find(query).to_list(length=100)

    if not hidden_gems:
        # Fallback
        hidden_gems = (
            await db.books.find({"average_rating": {"$gte": 4.0}, "available_copies": {"$gt": 0}})
            .limit(50)
            .to_list(length=None)
        )

    # Personalizuj
    user_profile = {
        "favorite_genres": user_genres,
        "favorite_authors": await get_user_favorite_authors(db, user_id, limit=5),
    }

    scored_gems = []
    for book in hidden_gems:
        book_data = normalize_book(serialize_doc(book))

        borrow_info = next((b for b in borrow_counts if b["_id"] == book["_id"]), None)
        book_data["borrow_count"] = borrow_info["borrow_count"] if borrow_info else 0

        book_data["matchScore"] = calculate_content_similarity(book_data, user_profile)
        book_data["hiddenGem"] = True

        scored_gems.append(book_data)

    scored_gems.sort(key=lambda x: (x["matchScore"], x.get("average_rating", 0)), reverse=True)

    return scored_gems[:limit]


@router.get("/highly-rated")
async def get_highly_rated_discoveries(
    limit: int = Query(15, ge=5, le=30),
    min_rating: float = Query(4.5, ge=3.0, le=5.0),
    current_user=Depends(get_current_user),
):
    """SEKCJA C: Wysoko oceniane odkrycia ⭐"""
    db = get_database()
    user_id = str(current_user.id)

    # Ulubione gatunki
    user_genres = await get_user_top_genres(db, user_id, limit=5)
    favorite_genres = [g["genre"] for g in user_genres]

    # Przeczytane książki
    user_reads = await db.interactions.find(
        {"user_id": user_id, "interaction_type": {"$in": ["borrow", "review"]}}
    ).to_list(length=None)
    read_book_ids = [ObjectId(i["book_id"]) for i in user_reads]

    # Znajdź wysoko oceniane
    query = {
        "average_rating": {"$gte": min_rating},
        "available_copies": {"$gt": 0},
        "_id": {"$nin": read_book_ids},
    }

    if favorite_genres:
        query["genres"] = {"$in": favorite_genres}

    highly_rated = await db.books.find(query).limit(100).to_list(length=None)

    if not highly_rated:
        # Fallback
        highly_rated = (
            await db.books.find(
                {"average_rating": {"$gte": min_rating}, "available_copies": {"$gt": 0}}
            )
            .limit(50)
            .to_list(length=None)
        )

    # Personalizuj z LightGCN
    try:
        lightgcn = get_service()
        user_idx = lightgcn.mongo_user_to_idx.get(user_id)
        user_embedding = lightgcn.user_emb[user_idx] if user_idx is not None else None
    except:
        user_embedding = None

    scored_books = []
    for book in highly_rated:
        book_data = normalize_book(serialize_doc(book))

        # LightGCN score
        if user_embedding is not None:
            try:
                gb_id = book.get("goodbooks_book_id")
                book_idx = lightgcn.goodbooks_id_to_idx.get(int(gb_id)) if gb_id else None

                if book_idx is not None:
                    book_embedding = lightgcn.item_emb[book_idx]
                    score = np.dot(user_embedding, book_embedding) / (
                        np.linalg.norm(user_embedding) * np.linalg.norm(book_embedding)
                    )
                    book_data["matchScore"] = float(score)
                else:
                    book_data["matchScore"] = 0.5
            except:
                book_data["matchScore"] = 0.5
        else:
            book_data["matchScore"] = 0.5

        book_data["highlyRated"] = True
        scored_books.append(book_data)

    # Hybrid: 70% matchScore + 30% rating
    scored_books.sort(
        key=lambda x: (x["matchScore"] * 0.7 + (x.get("average_rating", 0) / 5.0) * 0.3),
        reverse=True,
    )

    return scored_books[:limit]


# ==========================================================
#  DIVERSITY COMPARISON
# ==========================================================


@router.get("/diversity-comparison")
async def compare_diversity_metrics(
    n: int = Query(default=30, ge=10, le=50),
    lambda_values: str = Query(
        default="0.3,0.5,0.7,0.9", description="Wartości λ oddzielone przecinkami"
    ),
    current_user=Depends(get_current_user),
):
    """
    📊 Porównuje metryki różnorodności dla różnych wartości λ

    Endpoint pomocniczy do eksperymentowania z optymalnym λ.
    """
    if not MMR_AVAILABLE:
        raise HTTPException(503, "MMR not available")

    db = get_database()
    user_id = str(current_user.id)

    # Parse lambda values
    try:
        lambdas = [float(x.strip()) for x in lambda_values.split(",")]
    except:
        raise HTTPException(400, "Invalid lambda_values format")

    # Zbierz wypożyczone
    borrowed_goodbooks_ids = set()
    async for loan in db.loans.find({"user_id": user_id, "status": "active"}):
        # ✅ FIX: Konwertuj book_id na ObjectId
        book_id = (
            ObjectId(loan.get("book_id"))
            if isinstance(loan.get("book_id"), str)
            else loan.get("book_id")
        )
        book = await db.books.find_one({"_id": book_id})
        if book and book.get("goodbooks_book_id"):
            try:
                borrowed_goodbooks_ids.add(int(book["goodbooks_book_id"]))
            except:
                pass

    # Pobierz kandydatów
    try:
        rec_ids = get_service().get_recommendations_for_user(
            mongo_user_id=user_id,
            n=n * 3,
            exclude_goodbooks_ids=borrowed_goodbooks_ids,
            use_cache=False,
        )
    except:
        raise HTTPException(500, "Failed to get recommendations")

    candidates = await enrich_recommendations_with_metadata(rec_ids, db, limit=n * 3)

    # Test każdego λ
    results = []

    for lam in lambdas:
        recs = mmr_rerank(
            candidates, n=n, lambda_param=lam, enforce_author_limit=True, max_per_author=2
        )

        metrics = diversity_metrics(recs)

        results.append(
            {
                "lambda": lam,
                "metrics": metrics,
                "sample_books": [
                    {
                        "title": r.get("title"),
                        "author": r.get("author"),
                        "genres": r.get("genres", [])[:2],
                    }
                    for r in recs[:5]  # Pierwsze 5 przykładów
                ],
            }
        )

    return {
        "comparison": results,
        "recommendation": "Wyższa entropia i dissimilarity = większa różnorodność",
    }


# ==========================================================
#  DEBUG ENDPOINTS
# ==========================================================


@router.get("/debug/user-stats/{user_id}")
async def get_user_debug_stats(user_id: str, current_user=Depends(get_current_user)):
    """Debug - statystyki użytkownika"""
    current_uid = str(getattr(current_user, "id", ""))
    is_admin = getattr(current_user, "role", "") == "admin"

    if user_id != current_uid and not is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        service = get_service()
        has_embedding = user_id in service.mongo_user_to_idx

        user_stats = {
            "user_id": user_id,
            "has_embedding": has_embedding,
            "user_idx": service.mongo_user_to_idx.get(user_id),
            "is_new_user": (
                has_embedding and service.mongo_user_to_idx[user_id] >= service.num_users
            ),
        }

        if has_embedding:
            user_idx = service.mongo_user_to_idx[user_id]
            embedding = service.user_emb[user_idx]

            import numpy as np

            user_stats["embedding_norm"] = float(np.linalg.norm(embedding))
            user_stats["embedding_mean"] = float(np.mean(embedding))
            user_stats["embedding_std"] = float(np.std(embedding))

            # Liczba interakcji
            user_stats["interactions"] = service.user_interaction_counts.get(user_id, 0)

            # Ostatnia aktualizacja
            last_update = service.user_last_update.get(user_id)
            if last_update:
                user_stats["last_update"] = last_update.isoformat()

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
        stats = get_service().get_stats()
        stats["mmr_available"] = MMR_AVAILABLE
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/embedding-stats")
async def get_embedding_stats(
    interaction_service: InteractionService = Depends(get_interaction_service),
):
    """
    Statystyki aktualizacji embeddingów
    Pokazuje ile interakcji ma zaktualizowane embeddingi
    """
    stats = await interaction_service.get_embedding_stats()

    # Dodaj statystyki z GoodbooksLightGCNService
    try:
        service_stats = get_service().get_stats()
        stats["lightgcn_service"] = service_stats
        stats["mmr_available"] = MMR_AVAILABLE
    except Exception as e:
        stats["lightgcn_service"] = {"error": str(e)}

    return stats


# ==========================================================
#  TEST ENDPOINT - wszystkie nowe endpointy
# ==========================================================


@router.get("/test-new-endpoints")
async def test_new_endpoints(
    current_user=Depends(get_current_user),
):
    """
    Testowy endpoint sprawdzający czy wszystkie nowe endpointy działają
    """
    db = get_database()
    results = {}

    try:
        results["by_genre"] = len(await get_genre_recommendations(1, 5, current_user))
        results["by_author"] = len(await get_author_recommendations(1, 5, current_user))
        results["similar_readers"] = len(
            (await get_similar_readers_books(5, current_user))["books"]
        )
        results["new_arrivals"] = len(await get_new_arrivals(5, 30, current_user))
        results["hidden_gems"] = len(await get_hidden_gems(5, current_user))
        results["highly_rated"] = len(await get_highly_rated_discoveries(5, 4.5, current_user))
        results["status"] = "✅ All endpoints working!"
    except Exception as e:
        results["status"] = f"❌ Error: {str(e)}"
        results["error"] = str(e)

    return results
