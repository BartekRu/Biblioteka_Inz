
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Literal
from datetime import datetime
from bson import ObjectId
import random
import json
import logging
from pathlib import Path
from pydantic import BaseModel

# Internal imports
from .recommendation_helpers import (
    normalize_book,
    serialize_doc,
    enrich_recommendations_with_metadata,
    ensure_object_id,
)
from .user_analysis import get_user_top_genres
from ..database import get_database
from .auth import get_current_user
from ..models.dependencies import get_interaction_service
from ..service.interaction_service import InteractionService

# ML imports
import recommendation_engine.goodbooks_lightgcn_service as service_module
from recommendation_engine.goodbooks_lightgcn import MODEL_DIR

# MMR imports
try:
    from recommendation_engine.mmr_reranking import (
        mmr_rerank,
        apply_mmr_with_offset,
        diversity_metrics,
    )
    MMR_AVAILABLE = True
except ImportError:
    MMR_AVAILABLE = False
    print("⚠️ MMR re-ranking not available")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Main router
router = APIRouter()


# ==========================================================
#  HELPER: Lazy Loading Service
# ==========================================================


def get_service():
    """
    Pobierz serwis LightGCN (lazy loading)
    """
    if service_module.goodbooks_lgcn_service is None:
        raise HTTPException(
            status_code=503,
            detail="Recommendation service not initialized. Backend starting up..."
        )
    return service_module.goodbooks_lgcn_service


# ==========================================================
#  PYDANTIC MODELS
# ==========================================================


class InteractionIn(BaseModel):
    book_id: str
    interaction_type: Literal["view", "review", "borrow"]
    metadata: Optional[dict] = None


# ==========================================================
#  HEALTH & METRICS
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


@router.get("/metrics")
async def get_metrics():
    """Zwraca metryki modelu LightGCN + incremental stats"""
    model_dir = Path(MODEL_DIR)
    pro_file = model_dir / "lightgcn_goodbooks_pro_metrics.json"
    base_file = model_dir / "lightgcn_goodbooks_metrics.json"

    metrics_file = pro_file if pro_file.exists() else base_file
    base_metrics = {}

    if metrics_file and metrics_file.exists():
        with open(metrics_file, "r", encoding="utf-8") as f:
            base_metrics = json.load(f)

        try:
            last_updated = datetime.fromtimestamp(
                metrics_file.stat().st_mtime
            ).strftime("%Y-%m-%d")
        except Exception:
            last_updated = datetime.now().strftime("%Y-%m-%d")
    else:
        last_updated = datetime.now().strftime("%Y-%m-%d")

    # Incremental stats
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
        # Base metrics
        "recall20": base_metrics.get("recall20", 0.1411),
        "ndcg20": base_metrics.get("ndcg20", 0.0842),
        "precision20": base_metrics.get("precision20", 0.0623),
        "coverage": base_metrics.get("coverage", 0.78),
        "trainUsers": base_metrics.get("trainUsers", "53,175"),
        "trainItems": base_metrics.get("trainItems", "10,000"),
        "interactions": str(base_metrics.get("interactions", "932,940")),
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
#  BASIC ENDPOINTS
# ==========================================================


@router.get("/featured")
async def get_featured(
    limit: int = Query(default=10, le=20),
    current_user=Depends(get_current_user)
):
    """Featured recommendations based on user's favorite genres"""
    db = get_database()
    user_id = str(current_user.id)

    # Get favorite genres from loans
    favorite_genres = []
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
                        {"$cond": [
                            {"$isArray": "$book.genre"},
                            "$book.genre",
                            ["$book.genre"]
                        ]},
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

    # Find books
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

    # Fill with popular
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
    """Get book categories with sample covers"""
    db = get_database()

    pipeline = [
        {
            "$addFields": {
                "genres": {
                    "$cond": [
                        {"$isArray": "$genres"},
                        "$genres",
                        {"$cond": [
                            {"$isArray": "$genre"},
                            "$genre",
                            ["$genre"]
                        ]},
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
    limit: int = Query(default=3, le=5),
    current_user=Depends(get_current_user)
):
    """Recommendations based on currently borrowed books"""
    db = get_database()
    user_id = str(current_user.id)

    loans = (
        db.loans.find({"user_id": user_id, "status": "active"})
        .sort("borrowed_at", -1)
        .limit(limit)
    )

    sections = []

    async for loan in loans:
        book_id = ensure_object_id(loan["book_id"])
        raw = await db.books.find_one({"_id": book_id})
        if not raw:
            continue

        source = normalize_book(serialize_doc(raw))
        genres = source["genres"]
        author = source.get("author")

        # Find similar books
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


@router.get("/similar/{book_id}")
async def get_similar(book_id: str, limit: int = Query(default=8, le=20)):
    """Find similar books based on genre and author"""
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
#  INTERACTION TRACKING
# ==========================================================


@router.post("/interaction")
async def report_interaction(
    interaction: InteractionIn,
    current_user=Depends(get_current_user),
    interaction_service: InteractionService = Depends(get_interaction_service),
):
    """
    Raportuj interakcję + incremental update embeddingów
    """
    db = get_database()
    user_id = str(current_user.id)

    # Dodaj goodbooks_book_id do metadata
    meta = interaction.metadata or {}
    bid = ensure_object_id(interaction.book_id)
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
    offset: int = Query(default=0, ge=0),
    use_mmr: bool = Query(default=True),
    lambda_param: float = Query(default=0.7, ge=0.0, le=1.0),
    enforce_author_limit: bool = Query(default=True),
    max_per_author: int = Query(default=2, ge=1, le=10),
    current_user=Depends(get_current_user),
):
    """
    🎯 Główne rekomendacje LightGCN + MMR
    
    Features:
    - Collaborative filtering (LightGCN)
    - MMR re-ranking (diversity)
    - Exclude borrowed books
    - Author diversity limits
    """
    db = get_database()
    user_id = str(current_user.id)

    # Collect borrowed books
    borrowed_goodbooks_ids = set()
    borrowed_mongo_ids = set()

    async for loan in db.loans.find({"user_id": user_id, "status": "active"}):
        book_id = loan.get("book_id")
        if not book_id:
            continue

        borrowed_mongo_ids.add(str(book_id))
        book_id_obj = ensure_object_id(book_id)
        book = await db.books.find_one({"_id": book_id_obj})
        
        if book and book.get("goodbooks_book_id"):
            try:
                borrowed_goodbooks_ids.add(int(book["goodbooks_book_id"]))
            except (TypeError, ValueError):
                continue

    logger.info(
        f"📊 User {user_id} has {len(borrowed_goodbooks_ids)} borrowed books "
        f"(use_mmr={use_mmr}, λ={lambda_param})"
    )

    # Get LightGCN recommendations
    try:
        fetch_n = limit * 3 if use_mmr else limit

        rec_goodbooks_ids = get_service().get_recommendations_for_user(
            mongo_user_id=user_id,
            n=fetch_n,
            exclude_goodbooks_ids=borrowed_goodbooks_ids,
            use_cache=False,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()

        rec_goodbooks_ids = get_service().recommend_for_goodbooks_ids(
            list(borrowed_goodbooks_ids) if borrowed_goodbooks_ids else [],
            top_k=fetch_n
        )

    # Enrich with MongoDB data
    candidates = await enrich_recommendations_with_metadata(
        rec_goodbooks_ids, db, limit=fetch_n
    )
    candidates = [c for c in candidates if str(c["_id"]) not in borrowed_mongo_ids]

    logger.info(f"📚 Got {len(candidates)} candidates from LightGCN")

    # MMR RE-RANKING
    if use_mmr and MMR_AVAILABLE and len(candidates) > limit:
        logger.info(
            f"🔄 Applying MMR re-ranking (λ={lambda_param}, "
            f"author_limit={max_per_author})"
        )

        try:
            embeddings_dict = {}

            if offset > 0:
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

                div_metrics = diversity_metrics(results) if results else {}

                metadata = {
                    "model": "LightGCN + MMR",
                    "total_candidates": len(candidates),
                    "returned": len(results),
                    "offset": offset,
                    "next_offset": next_offset,
                    "mmr_lambda": lambda_param,
                    "diversity_metrics": div_metrics,
                }
            else:
                results = mmr_rerank(
                    candidates,
                    n=limit,
                    lambda_param=lambda_param,
                    embeddings_dict=embeddings_dict,
                    use_content_similarity=True,
                    enforce_author_limit=enforce_author_limit,
                    max_per_author=max_per_author,
                )

                div_metrics = diversity_metrics(results) if results else {}

                metadata = {
                    "model": "LightGCN + MMR",
                    "total_candidates": len(candidates),
                    "returned": len(results),
                    "mmr_lambda": lambda_param,
                    "diversity_metrics": div_metrics,
                }

            logger.info(
                f"✅ MMR complete: {len(results)} books, "
                f"{div_metrics.get('unique_authors', 0)} authors, "
                f"{div_metrics.get('unique_genres', 0)} genres"
            )

        except Exception as e:
            logger.error(f"❌ MMR failed: {e}, falling back")
            results = candidates[:limit]
            metadata = {"model": "LightGCN (MMR failed)", "error": str(e)}

    else:
        results = candidates[:limit]
        metadata = {"model": "LightGCN", "mmr_enabled": False}

    logger.info(f"✅ Returning {len(results)} recommendations")

    return {"recommendations": results, "metadata": metadata}


# ==========================================================
#  INCLUDE SUB-ROUTERS
# ==========================================================


def include_discovery_routes(main_router: APIRouter):
    """Include discovery endpoints from separate module"""
    from . import discovery_endpoints
    main_router.include_router(
        discovery_endpoints.router,
        tags=["discovery"]
    )


def include_debug_routes(main_router: APIRouter):
    """Include debug endpoints from separate module"""
    from . import debug_endpoints
    main_router.include_router(
        debug_endpoints.router,
        tags=["debug"]
    )


# Include sub-routers
include_discovery_routes(router)
include_debug_routes(router)


logger.info("📚 Recommendation routes configured successfully")
logger.info("🆕 NEW: Hidden Gems & Highly Rated endpoints available!")