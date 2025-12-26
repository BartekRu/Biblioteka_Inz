"""
routes/recommendations.py - FIXED VERSION
Recommendation endpoints using centralized RecommendationService
"""

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

# 🆕 FIXED: Import RecommendationService
from ..service.recommendation_service import get_recommendation_service

# Legacy ML imports (kept for backward compatibility)
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
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Main router
router = APIRouter()


# ==========================================================
#  CACHE MANAGEMENT
# ==========================================================

# Simple in-memory cache (replace with Redis in production)
_recommendation_cache = {}


def get_cache_key(user_id: str, params: dict) -> str:
    """Generate cache key from user_id and params"""
    param_str = "-".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"recs:{user_id}:{param_str}"


def invalidate_user_cache(user_id: str):
    """🆕 Invalidate all cached recommendations for user"""
    keys_to_remove = [k for k in _recommendation_cache if k.startswith(f"recs:{user_id}:")]
    for key in keys_to_remove:
        del _recommendation_cache[key]

    if keys_to_remove:
        logger.info(f"🗑️  Invalidated {len(keys_to_remove)} cache entries for user {user_id}")


# ==========================================================
#  HELPER: Legacy service (backward compatibility)
# ==========================================================


def get_service():
    """
    Get legacy GoodbooksLightGCNService (backward compatibility)
    """
    if service_module.goodbooks_lgcn_service is None:
        raise HTTPException(
            status_code=503, detail="Recommendation service not initialized. Backend starting up..."
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
    """Check recommendation system status"""
    try:
        # Check RecommendationService
        rec_service = get_recommendation_service()

        if rec_service is None:
            return {
                "status": "starting",
                "recommendation_service": "not_initialized",
                "timestamp": datetime.now().isoformat(),
            }

        # Get stats from legacy service
        stats = get_service().get_stats()

        return {
            "status": "healthy",
            "model_loaded": True,
            "recommendation_service": "initialized",  # 🆕
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
    """Return LightGCN model metrics + incremental stats"""
    model_dir = Path(MODEL_DIR)
    pro_file = model_dir / "lightgcn_goodbooks_pro_metrics.json"
    base_file = model_dir / "lightgcn_goodbooks_metrics.json"

    metrics_file = pro_file if pro_file.exists() else base_file
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
#  🆕 DIAGNOSTICS (NEW)
# ==========================================================


@router.get("/user/embedding-info")
async def get_user_embedding_info(current_user=Depends(get_current_user)):
    """
    🆕 Get diagnostic info about user's embedding

    Useful for debugging why recommendations aren't changing
    """
    user_id = str(current_user.id)

    rec_service = get_recommendation_service()
    if not rec_service:
        raise HTTPException(503, "Recommendation service not available")

    info = await rec_service.get_user_embedding_info(user_id)

    return info


@router.post("/cache/clear")
async def clear_user_cache(current_user=Depends(get_current_user)):
    """
    🆕 Manually clear recommendation cache

    Use when recommendations seem stuck
    """
    user_id = str(current_user.id)
    invalidate_user_cache(user_id)

    return {
        "message": "Cache cleared. Next recommendation request will use fresh embeddings.",
        "user_id": user_id,
    }


# ==========================================================
#  INTERACTION TRACKING (FIXED)
# ==========================================================


@router.post("/interaction")
async def report_interaction(
    interaction: InteractionIn,
    current_user=Depends(get_current_user),
    interaction_service: InteractionService = Depends(get_interaction_service),
):
    """
    Report user interaction + incremental embedding update

    🆕 FIXED: Now invalidates cache after embedding update
    """
    db = get_database()
    user_id = str(current_user.id)

    # Add goodbooks_book_id to metadata
    meta = interaction.metadata or {}
    bid = ensure_object_id(interaction.book_id)
    book = await db.books.find_one({"_id": bid})

    if book and book.get("goodbooks_book_id") is not None:
        try:
            meta["goodbooks_book_id"] = int(book["goodbooks_book_id"])
        except (TypeError, ValueError):
            pass

    # Create interaction (this will update embedding via InteractionService)
    result = await interaction_service.create_interaction(
        user_id=user_id,
        book_id=interaction.book_id,
        interaction_type=interaction.interaction_type,
        metadata=meta,
        update_embedding=True,
    )

    # 🆕 Invalidate cache if embedding was updated
    if result.get("embedding_updated"):
        invalidate_user_cache(user_id)
        logger.info(f"🗑️  Cache invalidated for user {user_id} after {interaction.interaction_type}")

    return {
        "status": "recorded",
        **result,
        "cache_invalidated": result.get("embedding_updated", False),  # 🆕
    }


# ==========================================================
#  🎯 MAIN RECOMMENDATION ENDPOINT (FIXED)
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
    🎯 Main LightGCN recommendations + MMR

    🆕 FIXED: Now uses RecommendationService with:
    - Cache checking (bypass if recent interaction)
    - Cold-start detection and hybrid approach
    - Proper embedding updates

    Features:
    - Collaborative filtering (LightGCN)
    - MMR re-ranking (diversity)
    - Exclude borrowed books
    - Author diversity limits
    - Real-time embedding updates
    """
    db = get_database()
    user_id = str(current_user.id)

    # 🆕 Get RecommendationService
    rec_service = get_recommendation_service()
    if not rec_service:
        # Fallback to legacy service if RecommendationService not available
        logger.warning("RecommendationService not available, using legacy service")
        return await _legacy_get_recommendations(
            user_id, limit, offset, use_mmr, lambda_param, enforce_author_limit, max_per_author, db
        )

    # 🆕 Check cache (bypass if recent interaction)
    cache_key = get_cache_key(
        user_id,
        {
            "n": limit,
            "offset": offset,
            "use_mmr": use_mmr,
            "lambda": lambda_param,
            "author_limit": enforce_author_limit,
            "max_per_author": max_per_author,
        },
    )

    use_cache = True
    recent_interaction = await db.interactions.find_one(
        {"user_id": user_id}, sort=[("created_at", -1)]
    )

    if recent_interaction:
        time_since_interaction = (
            datetime.utcnow() - recent_interaction["created_at"]
        ).total_seconds()
        if time_since_interaction < 300:  # 5 minutes
            use_cache = False
            logger.info(
                f"🔄 Recent interaction detected ({time_since_interaction:.0f}s ago) → bypassing cache"
            )

    if use_cache and cache_key in _recommendation_cache:
        logger.info(f"✅ Cache hit for user {user_id}")
        return _recommendation_cache[cache_key]

    # 🆕 Check if user is cold-start
    interactions_count = await db.interactions.count_documents({"user_id": user_id})
    is_cold_start = interactions_count < 5

    if is_cold_start:
        logger.info(f"❄️  User {user_id} is cold-start ({interactions_count} interactions)")

    # Collect borrowed books to exclude
    borrowed_book_ids = []
    async for loan in db.loans.find({"user_id": user_id, "status": "active"}):
        book_id = loan.get("book_id")
        if book_id:
            borrowed_book_ids.append(str(book_id))

    logger.info(
        f"📊 User {user_id} has {len(borrowed_book_ids)} borrowed books (use_mmr={use_mmr}, λ={lambda_param})"
    )

    # 🆕 Get recommendations using RecommendationService
    try:
        if is_cold_start:
            # Hybrid: 60% LightGCN + 40% Content-based
            lightgcn_recs = await rec_service.get_recommendations(
                user_id=user_id, n=int(limit * 0.6), exclude_books=borrowed_book_ids
            )

            content_recs = await rec_service.get_content_based_recommendations(
                user_id=user_id, n=int(limit * 0.4)
            )

            # Merge
            all_recs = lightgcn_recs + content_recs
        else:
            # Normal: LightGCN only (fetch more for MMR)
            fetch_n = limit * 3 if use_mmr else limit
            all_recs = await rec_service.get_recommendations(
                user_id=user_id, n=fetch_n, exclude_books=borrowed_book_ids
            )

        # Convert to format expected by enrich function
        # all_recs has format: [{book_id, goodbooks_id, score}, ...]
        # We need goodbooks_ids list for enrich function
        goodbooks_ids_for_enrich = [r["goodbooks_id"] for r in all_recs if r.get("goodbooks_id")]

        # Enrich with MongoDB data
        candidates = await enrich_recommendations_with_metadata(
            goodbooks_ids_for_enrich, db, limit=len(goodbooks_ids_for_enrich)
        )

        logger.info(f"📚 Got {len(candidates)} candidates")

        # MMR RE-RANKING
        if use_mmr and MMR_AVAILABLE and len(candidates) > limit:
            logger.info(
                f"🔄 Applying MMR re-ranking (λ={lambda_param}, author_limit={max_per_author})"
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
                        "model": "LightGCN + MMR (via RecommendationService)",
                        "total_candidates": len(candidates),
                        "returned": len(results),
                        "offset": offset,
                        "next_offset": next_offset,
                        "mmr_lambda": lambda_param,
                        "diversity_metrics": div_metrics,
                        "is_cold_start": is_cold_start,  # 🆕
                        "interactions_count": interactions_count,  # 🆕
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
                        "model": "LightGCN + MMR (via RecommendationService)",
                        "total_candidates": len(candidates),
                        "returned": len(results),
                        "mmr_lambda": lambda_param,
                        "diversity_metrics": div_metrics,
                        "is_cold_start": is_cold_start,  # 🆕
                        "interactions_count": interactions_count,  # 🆕
                    }

                logger.info(
                    f"✅ MMR complete: {len(results)} books, "
                    f"{div_metrics.get('unique_authors', 0)} authors, "
                    f"{div_metrics.get('unique_genres', 0)} genres"
                )

            except Exception as e:
                logger.error(f"❌ MMR failed: {e}, falling back")
                results = candidates[:limit]
                metadata = {
                    "model": "LightGCN (MMR failed)",
                    "error": str(e),
                    "is_cold_start": is_cold_start,
                }

        else:
            results = candidates[:limit]
            metadata = {
                "model": "LightGCN (via RecommendationService)",
                "mmr_enabled": False,
                "is_cold_start": is_cold_start,
                "interactions_count": interactions_count,
            }

    except Exception as e:
        logger.error(f"❌ Recommendations failed: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get recommendations: {str(e)}")

    # 🆕 Cache if not cold-start
    response = {"recommendations": results, "metadata": metadata}

    if not is_cold_start and use_cache:
        _recommendation_cache[cache_key] = response

    logger.info(f"✅ Returning {len(results)} recommendations")

    return response


# ==========================================================
#  LEGACY FALLBACK (backward compatibility)
# ==========================================================


async def _legacy_get_recommendations(
    user_id: str,
    limit: int,
    offset: int,
    use_mmr: bool,
    lambda_param: float,
    enforce_author_limit: bool,
    max_per_author: int,
    db,
):
    """
    Legacy recommendation method (backward compatibility)
    Uses old get_service() directly
    """
    logger.warning("Using legacy recommendation method")

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
        logger.error(f"Legacy service failed: {e}")
        rec_goodbooks_ids = []

    # Enrich
    candidates = await enrich_recommendations_with_metadata(rec_goodbooks_ids, db, limit=fetch_n)
    candidates = [c for c in candidates if str(c["_id"]) not in borrowed_mongo_ids]

    # MMR if requested
    if use_mmr and MMR_AVAILABLE and len(candidates) > limit:
        results = mmr_rerank(
            candidates,
            n=limit,
            lambda_param=lambda_param,
            embeddings_dict={},
            use_content_similarity=True,
            enforce_author_limit=enforce_author_limit,
            max_per_author=max_per_author,
        )
        metadata = {"model": "LightGCN + MMR (legacy)", "mmr_lambda": lambda_param}
    else:
        results = candidates[:limit]
        metadata = {"model": "LightGCN (legacy)", "mmr_enabled": False}

    return {"recommendations": results, "metadata": metadata}


# ==========================================================
#  BASIC ENDPOINTS (unchanged - kept for compatibility)
# ==========================================================


@router.get("/featured")
async def get_featured(
    limit: int = Query(default=10, le=20), current_user=Depends(get_current_user)
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

    # Fill with popular if needed
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
    """Recommendations based on currently borrowed books"""
    db = get_database()
    user_id = str(current_user.id)

    loans = (
        db.loans.find({"user_id": user_id, "status": "active"}).sort("borrowed_at", -1).limit(limit)
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
#  INCLUDE SUB-ROUTERS (unchanged)
# ==========================================================


def include_discovery_routes(main_router: APIRouter):
    """Include discovery endpoints from separate module"""
    from . import discovery_endpoints

    main_router.include_router(discovery_endpoints.router, tags=["discovery"])


def include_debug_routes(main_router: APIRouter):
    """Include debug endpoints from separate module"""
    from . import debug_endpoints

    main_router.include_router(debug_endpoints.router, tags=["debug"])


# Include sub-routers
include_discovery_routes(router)
include_debug_routes(router)


logger.info("📚 Recommendation routes configured successfully (using RecommendationService)")
logger.info("🆕 NEW: Real-time embeddings + Cache invalidation + Diagnostics!")
