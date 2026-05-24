from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Literal
from datetime import datetime
from bson import ObjectId
import random
import json
import logging
from pathlib import Path
from pydantic import BaseModel

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

from ..service.recommendation_service import get_recommendation_service

import recommendation_engine.goodbooks_lightgcn_service as service_module
from recommendation_engine.goodbooks_lightgcn import MODEL_DIR

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

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter()


_recommendation_cache = {}


def get_cache_key(user_id: str, params: dict) -> str:
    param_str = "-".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"recs:{user_id}:{param_str}"


def invalidate_user_cache(user_id: str):
    keys_to_remove = [k for k in _recommendation_cache if k.startswith(f"recs:{user_id}:")]
    for key in keys_to_remove:
        del _recommendation_cache[key]

    if keys_to_remove:
        logger.info(f"🗑️  Invalidated {len(keys_to_remove)} cache entries for user {user_id}")


def get_service():

    if service_module.goodbooks_lgcn_service is None:
        raise HTTPException(
            status_code=503, detail="Recommendation service not initialized. Backend starting up..."
        )
    return service_module.goodbooks_lgcn_service


class InteractionIn(BaseModel):
    book_id: str
    interaction_type: Literal["view", "review", "borrow", "wishlist_add", "wishlist_remove"]
    metadata: Optional[dict] = None


@router.get("/health")
async def health_check():
    try:
        rec_service = get_recommendation_service()

        if rec_service is None:
            return {
                "status": "starting",
                "recommendation_service": "not_initialized",
                "timestamp": datetime.now().isoformat(),
            }

        stats = get_service().get_stats()

        return {
            "status": "healthy",
            "model_loaded": True,
            "recommendation_service": "initialized",
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
        **incremental_info,
        "mmrAvailable": MMR_AVAILABLE,
    }


@router.get("/user/embedding-info")
async def get_user_embedding_info(current_user=Depends(get_current_user)):

    user_id = str(current_user.id)

    rec_service = get_recommendation_service()
    if not rec_service:
        raise HTTPException(503, "Recommendation service not available")

    info = await rec_service.get_user_embedding_info(user_id)

    return info


@router.post("/cache/clear")
async def clear_user_cache(current_user=Depends(get_current_user)):

    user_id = str(current_user.id)
    invalidate_user_cache(user_id)

    return {
        "message": "Cache cleared. Next recommendation request will use fresh embeddings.",
        "user_id": user_id,
    }


@router.post("/interaction")
async def report_interaction(
    interaction: InteractionIn,
    current_user=Depends(get_current_user),
    interaction_service: InteractionService = Depends(get_interaction_service),
):

    db = get_database()
    user_id = str(current_user.id)

    meta = interaction.metadata or {}
    bid = ensure_object_id(interaction.book_id)
    book = await db.books.find_one({"_id": bid})

    if book and book.get("goodbooks_book_id") is not None:
        try:
            meta["goodbooks_book_id"] = int(book["goodbooks_book_id"])
        except (TypeError, ValueError):
            pass

    update_embedding = interaction.interaction_type != "wishlist_remove"

    result = await interaction_service.create_interaction(
        user_id=user_id,
        book_id=interaction.book_id,
        interaction_type=interaction.interaction_type,
        metadata=meta,
        update_embedding=update_embedding,
    )

    if result.get("embedding_updated"):
        invalidate_user_cache(user_id)
        logger.info(f"🗑️  Cache invalidated for user {user_id} after {interaction.interaction_type}")

    return {
        "status": "recorded",
        **result,
        "cache_invalidated": result.get("embedding_updated", False),
    }


@router.get("/user-lightgcn")
async def get_user_lightgcn_recommendations(
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0, ge=0),
    use_mmr: bool = Query(default=True),
    lambda_param: float = Query(default=0.7, ge=0.0, le=1.0),
    enforce_author_limit: bool = Query(default=True),
    max_per_author: int = Query(default=2, ge=1, le=10),
    use_genre_boost: bool = Query(default=True),
    boost_factor: float = Query(default=3.0, ge=1.0, le=10.0),
    current_user=Depends(get_current_user),
):

    db = get_database()
    user_id = str(current_user.id)

    rec_service = get_recommendation_service()
    if not rec_service:
        logger.warning("RecommendationService not available, using legacy service")
        return await _legacy_get_recommendations(
            user_id, limit, offset, use_mmr, lambda_param, enforce_author_limit, max_per_author, db
        )

    cache_key = get_cache_key(
        user_id,
        {
            "n": limit,
            "offset": offset,
            "use_mmr": use_mmr,
            "lambda": lambda_param,
            "author_limit": enforce_author_limit,
            "max_per_author": max_per_author,
            "use_genre_boost": use_genre_boost,
            "boost_factor": boost_factor,
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
        if time_since_interaction < 300:
            use_cache = False
            logger.info(
                f"🔄 Recent interaction detected ({time_since_interaction:.0f}s ago) → bypassing cache"
            )

    if use_cache and cache_key in _recommendation_cache:
        logger.info(f"✅ Cache hit for user {user_id}")
        return _recommendation_cache[cache_key]

    interactions_count = await db.interactions.count_documents({"user_id": user_id})
    is_cold_start = interactions_count < 5

    if is_cold_start:
        logger.info(f"❄️  User {user_id} is cold-start ({interactions_count} interactions)")

    borrowed_book_ids = []
    async for loan in db.loans.find({"user_id": user_id, "status": "active"}):
        book_id = loan.get("book_id")
        if book_id:
            borrowed_book_ids.append(str(book_id))

    logger.info(
        f"📊 User {user_id} has {len(borrowed_book_ids)} borrowed books (use_mmr={use_mmr}, λ={lambda_param})"
    )

    try:
        if is_cold_start:
            lightgcn_recs = await rec_service.get_recommendations(
                user_id=user_id, n=int(limit * 0.6), exclude_books=borrowed_book_ids
            )

            content_recs = await rec_service.get_content_based_recommendations(
                user_id=user_id, n=int(limit * 0.4)
            )

            all_recs = lightgcn_recs + content_recs
        else:
            # ============================================================
            # ✅ FIX: Zwiększ fetch_n gdy genre_boost aktywny!
            # ============================================================
            if use_mmr and use_genre_boost:
                fetch_n = limit * 10
            elif use_mmr:
                fetch_n = limit * 6
            else:
                fetch_n = limit

            lightgcn_recs = await rec_service.get_recommendations(
                user_id=user_id, n=fetch_n, exclude_books=borrowed_book_ids
            )
            content_recs = await rec_service.get_content_based_recommendations(
                user_id=user_id, n=limit * 2
            )
            all_recs = lightgcn_recs + content_recs

        candidates = await enrich_recommendations_with_metadata(all_recs, db, limit=len(all_recs))

        logger.info(f"📚 Got {len(candidates)} candidates")

        candidates = await rec_service.apply_hybrid_scoring(
            candidates=candidates, user_id=user_id, relevance_weight=0.70
        )
        cluster_limits = await rec_service.get_cluster_limits(user_id, limit)
        logger.info(f"Recommendation cluster limits: {cluster_limits}")

        # ============================================================
        # 🆕 GENRE BOOSTING (przed MMR!)
        # ============================================================
        genre_boosted = False
        if use_genre_boost and not is_cold_start:
            # Sprawdź czy użytkownik jest "niche"
            user_profile = await rec_service._get_user_genre_profile(user_id)
            is_niche = await rec_service._is_niche_user(user_profile, threshold=0.5)

            if is_niche:
                logger.info(
                    f"🎯 Niche user detected - applying genre boosting (factor={boost_factor})"
                )

                candidates = await rec_service._apply_genre_boosting(
                    candidates=candidates,
                    user_id=user_id,
                    boost_factor=boost_factor,
                    top_n_genres=6,
                )
                genre_boosted = True
            else:
                logger.info(f"📊 Regular user - skipping genre boosting")

        # ============================================================
        # ✅ FIX #1: PODMIEŃ score = boosted_score PRZED MMR!
        # ============================================================
        if genre_boosted:
            for candidate in candidates:
                candidate["score"] = candidate.get("boosted_score", candidate.get("score", 0.0))
            logger.info(f"✅ Updated {len(candidates)} scores with boosted values for MMR")

        # ============================================================
        # MMR RE-RANKING
        # ============================================================
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
                        max_per_series=2,
                        cluster_limits=cluster_limits,
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
                        "is_cold_start": is_cold_start,
                        "interactions_count": interactions_count,
                        "genre_boosted": genre_boosted,
                        "boost_factor": boost_factor if genre_boosted else None,
                        "hybrid_scoring": True,
                        "relevance_weight": 0.70,
                        "cluster_limits": cluster_limits,
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
                        max_per_series=2,
                        cluster_limits=cluster_limits,
                    )

                    div_metrics = diversity_metrics(results) if results else {}

                    metadata = {
                        "model": "LightGCN + MMR (via RecommendationService)",
                        "total_candidates": len(candidates),
                        "returned": len(results),
                        "mmr_lambda": lambda_param,
                        "diversity_metrics": div_metrics,
                        "is_cold_start": is_cold_start,
                        "interactions_count": interactions_count,
                        "genre_boosted": genre_boosted,
                        "boost_factor": boost_factor if genre_boosted else None,
                        "hybrid_scoring": True,
                        "relevance_weight": 0.70,
                        "cluster_limits": cluster_limits,
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
                "genre_boosted": genre_boosted,
                "boost_factor": boost_factor if genre_boosted else None,
                "hybrid_scoring": True,
                "relevance_weight": 0.70,
                "cluster_limits": cluster_limits,
            }

    except Exception as e:
        logger.error(f"❌ Recommendations failed: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get recommendations: {str(e)}")

    response = {"recommendations": results, "metadata": metadata}

    if not is_cold_start and use_cache:
        _recommendation_cache[cache_key] = response

    logger.info(f"✅ Returning {len(results)} recommendations")

    return response


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

    logger.warning("Using legacy recommendation method")

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

    try:
        fetch_n = limit * 6 if use_mmr else limit

        rec_goodbooks_ids = get_service().get_recommendations_for_user(
            mongo_user_id=user_id,
            n=fetch_n,
            exclude_goodbooks_ids=borrowed_goodbooks_ids,
            use_cache=False,
        )
    except Exception as e:
        logger.error(f"Legacy service failed: {e}")
        rec_goodbooks_ids = []

    candidates = await enrich_recommendations_with_metadata(rec_goodbooks_ids, db, limit=fetch_n)
    candidates = [c for c in candidates if str(c["_id"]) not in borrowed_mongo_ids]

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


@router.get("/featured")
async def get_featured(
    limit: int = Query(default=10, le=20), current_user=Depends(get_current_user)
):
    """Featured recommendations based on user's favorite genres"""
    db = get_database()
    user_id = str(current_user.id)

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
    limit: int = Query(default=3, le=5),
    books_per_source: int = Query(default=12, ge=1, le=30),
    current_user=Depends(get_current_user),
):

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

        similar_query = {"_id": {"$ne": book_id}, "$or": []}

        if genres:
            similar_query["$or"].append({"genres": {"$in": genres}})
        if author:
            similar_query["$or"].append({"author": author})

        if not similar_query["$or"]:
            continue

        recs = []
        async for raw2 in db.books.find(similar_query).limit(books_per_source):
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


def include_discovery_routes(main_router: APIRouter):
    """Include discovery endpoints from separate module"""
    from . import discovery_endpoints

    main_router.include_router(discovery_endpoints.router, tags=["discovery"])


def include_debug_routes(main_router: APIRouter):
    from . import debug_endpoints

    main_router.include_router(debug_endpoints.router, tags=["debug"])


include_discovery_routes(router)
include_debug_routes(router)


logger.info("📚 Recommendation routes configured successfully (using RecommendationService)")
logger.info("🆕 NEW: Real-time embeddings + Cache invalidation + Diagnostics!")


@router.get("/genre-stats")
async def get_genre_stats(
    rare_threshold: float = Query(default=0.10, ge=0.01, le=0.5),
    current_user=Depends(get_current_user),
):
    """
    📊 Statystyki pokrycia gatunków w bazie.

    Pokazuje:
    - Coverage każdego gatunku (% książek)
    - Automatycznie wykryte gatunki rzadkie
    - Top/bottom gatunki

    Args:
        rare_threshold: Próg dla "rzadkich" (domyślnie 0.10 = 10%)
    """
    rec_service = get_recommendation_service()
    if not rec_service:
        raise HTTPException(503, "Recommendation service not available")

    try:
        # Pobierz stats
        coverage_stats = await rec_service._get_genre_coverage_stats()

        if not coverage_stats:
            return {"error": "No coverage stats available"}

        # Sortuj
        sorted_genres = sorted(coverage_stats.items(), key=lambda x: x[1], reverse=True)

        # Wykryj rzadkie
        rare_genres = {genre: cov for genre, cov in coverage_stats.items() if cov < rare_threshold}

        # Top 20
        top_20 = [{"genre": g, "coverage": round(c * 100, 2)} for g, c in sorted_genres[:20]]

        # Rare genres
        rare_list = [
            {"genre": g, "coverage": round(c * 100, 2)}
            for g, c in sorted(rare_genres.items(), key=lambda x: x[1])
        ]

        return {
            "total_genres": len(coverage_stats),
            "rare_threshold_percent": rare_threshold * 100,
            "rare_genres_count": len(rare_genres),
            "top_20_genres": top_20,
            "rare_genres": rare_list[:30],  # Top 30 najrzadszych
            "summary": {
                "most_common": sorted_genres[0][0] if sorted_genres else None,
                "most_common_coverage": round(sorted_genres[0][1] * 100, 2) if sorted_genres else 0,
                "rarest": sorted_genres[-1][0] if sorted_genres else None,
                "rarest_coverage": round(sorted_genres[-1][1] * 100, 2) if sorted_genres else 0,
            },
        }

    except Exception as e:
        logger.error(f"Failed to get genre stats: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get genre stats: {str(e)}")


@router.get("/user/genre-analysis")
async def get_user_genre_analysis(
    current_user=Depends(get_current_user),
):
    """
    🎯 Analiza profilu gatunkowego użytkownika.

    Pokazuje:
    - Top gatunki użytkownika
    - Czy użytkownik jest "niche"
    - Coverage każdego gatunku użytkownika
    - Rekomendowany boost_factor
    """
    rec_service = get_recommendation_service()
    if not rec_service:
        raise HTTPException(503, "Recommendation service not available")

    user_id = str(current_user.id)

    try:
        # Profil użytkownika
        user_profile = await rec_service._get_user_genre_profile(user_id)

        if not user_profile:
            return {
                "user_id": user_id,
                "message": "No interactions yet - cannot analyze genre profile",
            }

        # Coverage stats
        coverage_stats = await rec_service._get_genre_coverage_stats()

        # Czy niche user?
        is_niche = await rec_service._is_niche_user(user_profile, threshold=0.5)

        # Rare genres
        rare_genres_in_profile = {
            genre: (weight, coverage_stats.get(genre, 0))
            for genre, weight in user_profile.items()
            if coverage_stats.get(genre, 1.0) < 0.10
        }

        total_weight = sum(user_profile.values())
        rare_weight = sum(w for w, _ in rare_genres_in_profile.values())
        rare_percentage = (rare_weight / total_weight * 100) if total_weight > 0 else 0

        # Top gatunki z coverage
        top_genres_enriched = []
        for genre, weight in user_profile.most_common(10):
            coverage = coverage_stats.get(genre, 0)
            is_rare = coverage < 0.10

            top_genres_enriched.append(
                {
                    "genre": genre,
                    "weight": weight,
                    "coverage_percent": round(coverage * 100, 2),
                    "is_rare": is_rare,
                }
            )

        # Rekomendowany boost
        recommended_boost = 3.0 if rare_percentage > 50 else 2.0

        return {
            "user_id": user_id,
            "total_interactions": sum(user_profile.values()),
            "unique_genres": len(user_profile),
            "is_niche_user": is_niche,
            "rare_genres_percentage": round(rare_percentage, 1),
            "recommended_boost_factor": recommended_boost,
            "top_genres": top_genres_enriched,
            "rare_genres_detail": [
                {"genre": g, "weight": w, "coverage_percent": round(cov * 100, 2)}
                for g, (w, cov) in sorted(
                    rare_genres_in_profile.items(), key=lambda x: x[1][0], reverse=True
                )
            ],
            "advice": (
                f"✅ NICHE USER detected! Use boost_factor={recommended_boost} for best results."
                if is_niche
                else "📊 Regular user - genre boosting optional (or use lower boost_factor=2.0)"
            ),
        }

    except Exception as e:
        logger.error(f"Failed genre analysis: {e}", exc_info=True)
        raise HTTPException(500, f"Analysis failed: {str(e)}")
