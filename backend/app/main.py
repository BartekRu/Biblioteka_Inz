"""
main.py - FIXED VERSION
FastAPI application with complete RecommendationService integration
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# Database
from .database import connect_to_mongo, close_mongo_connection, get_database

# Routes
from .routes import auth, books, users, loans, reviews, views
from .routes.recommendations import router as recommendations_router

# Recommendation services
from recommendation_engine.goodbooks_lightgcn_service import get_service
import recommendation_engine.goodbooks_lightgcn_service as service_module

# 🆕 FIXED: Poprawna ścieżka importu (services z 's')
from app.service.lightgcn_adapter import LightGCNAdapter
from app.service.recommendation_service import (
    initialize_recommendation_service,
    get_recommendation_service,
)

# Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager with COMPLETE service initialization:
    1. MongoDB connection
    2. GoodbooksLightGCNService (model)
    3. LightGCNAdapter (MongoDB <-> Goodbooks conversion)
    4. RecommendationService (orchestration)
    """
    logger.info("🚀 Starting FastAPI application v2.0 (with RecommendationService)...")

    # =========================================================================
    # STEP 1: Connect to MongoDB
    # =========================================================================
    await connect_to_mongo()
    logger.info("✅ Connected to MongoDB")

    db = get_database()

    # =========================================================================
    # STEP 2: Initialize GoodbooksLightGCNService (base model)
    # =========================================================================
    logger.info("📊 Initializing GoodbooksLightGCNService...")
    try:
        lightgcn_service = get_service(db=db)
        service_module.goodbooks_lgcn_service = lightgcn_service
        logger.info(
            f"✅ GoodbooksLightGCNService loaded: {lightgcn_service.num_users:,} users, {lightgcn_service.num_items:,} items"
        )
    except Exception as e:
        logger.error(f"❌ Failed to initialize GoodbooksLightGCNService: {e}")
        raise

    # =========================================================================
    # STEP 3: Initialize LightGCNAdapter (MongoDB <-> Goodbooks conversion)
    # =========================================================================
    logger.info("🔄 Initializing LightGCNAdapter...")
    try:
        lightgcn_adapter = LightGCNAdapter(lightgcn_service=lightgcn_service, db=db)
        logger.info("✅ LightGCNAdapter initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize LightGCNAdapter: {e}")
        raise

    # =========================================================================
    # STEP 4: Initialize RecommendationService (high-level orchestration)
    # =========================================================================
    logger.info("🎯 Initializing RecommendationService...")
    try:
        recommendation_service = initialize_recommendation_service(
            lightgcn_service=lightgcn_service, lightgcn_adapter=lightgcn_adapter, db=db
        )
        logger.info("✅ RecommendationService initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize RecommendationService: {e}")
        raise

    # =========================================================================
    # STEP 5: Display statistics
    # =========================================================================
    try:
        interactions_count = await db.interactions.count_documents({})
        logger.info(f"📊 Total interactions in DB: {interactions_count}")

        # Stats per type
        pipeline = [{"$group": {"_id": "$interaction_type", "count": {"$sum": 1}}}]
        stats = await db.interactions.aggregate(pipeline).to_list(length=None)
        for stat in stats:
            logger.info(f"   - {stat['_id']}: {stat['count']}")

        # 🆕 Display embedding stats
        embeddings_updated = await db.interactions.count_documents({"embedding_updated": True})
        if embeddings_updated > 0:
            logger.info(
                f"🧠 Embeddings updated: {embeddings_updated}/{interactions_count} ({embeddings_updated/interactions_count*100:.1f}%)"
            )
        else:
            logger.info("🧠 No embeddings updated yet (first startup or migration pending)")

    except Exception as e:
        logger.warning(f"⚠️  Failed to get statistics: {e}")

    logger.info("=" * 80)
    logger.info("✅ Application startup complete!")
    logger.info("📚 Recommendation features available:")
    logger.info("   - LightGCN collaborative filtering")
    logger.info("   - Real-time embedding updates")
    logger.info("   - Content-based cold-start handling")
    logger.info("   - MMR diversity re-ranking")
    logger.info("   - Hidden Gems & Highly Rated discovery")
    logger.info("=" * 80)

    yield

    # Shutdown
    logger.info("👋 Shutting down...")
    await close_mongo_connection()
    logger.info("✅ MongoDB connection closed")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Biblioteka_Inz API",
    description="AI-powered library management system with LightGCN recommendations and real-time personalization",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev
        "http://localhost:5173",  # Vite dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Register Routers
# ============================================================================

app.include_router(auth.router, prefix="/v1/auth", tags=["Authentication"])
app.include_router(books.router, prefix="/v1/books", tags=["Books"])
app.include_router(users.router, prefix="/v1/users", tags=["Users"])
app.include_router(loans.router, prefix="/v1/loans", tags=["Loans"])
app.include_router(reviews.router, prefix="/v1/reviews", tags=["Reviews"])
app.include_router(views.router, prefix="/v1/views", tags=["Views"])
app.include_router(recommendations_router, prefix="/v1/recommendations", tags=["Recommendations"])


# ============================================================================
# Root & Health Endpoints
# ============================================================================


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Biblioteka_Inz API",
        "version": "2.0.0",
        "features": [
            "LightGCN collaborative filtering",
            "Real-time embedding updates",
            "Content-based cold-start handling",
            "MMR diversity re-ranking",
            "Interaction tracking (view, borrow, review)",
            "🆕 Centralized RecommendationService",
            "🆕 Hidden Gems discovery",
            "🆕 Highly Rated recommendations",
            "🆕 Genre & Author personalization",
            "🆕 Similar Readers collaborative filtering",
        ],
        "docs": "/docs",
        "redoc": "/redoc",
        "key_endpoints": [
            "/v1/recommendations/user-lightgcn",
            "/v1/recommendations/user/embedding-info",
            "/v1/recommendations/hidden-gems",
            "/v1/recommendations/highly-rated",
            "/v1/recommendations/interaction",
        ],
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db = get_database()

    # Check MongoDB
    try:
        await db.command("ping")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    # Check LightGCN service
    lightgcn_status = (
        "healthy"
        if hasattr(service_module, "goodbooks_lgcn_service")
        and service_module.goodbooks_lgcn_service is not None
        else "not_initialized"
    )

    # Check RecommendationService
    rec_service = get_recommendation_service()
    rec_service_status = "healthy" if rec_service is not None else "not_initialized"

    return {
        "status": (
            "healthy"
            if db_status == "healthy"
            and lightgcn_status == "healthy"
            and rec_service_status == "healthy"
            else "degraded"
        ),
        "database": db_status,
        "lightgcn_service": lightgcn_status,
        "recommendation_service": rec_service_status,  # 🆕
        "version": "2.0.0",
        "features": ["real_time_embeddings", "content_based_fallback", "mmr_diversity"],
    }


@app.get("/v1/stats")
async def get_stats():
    """
    System statistics
    """
    db = get_database()

    try:
        # Basic stats
        stats = {
            "users": await db.users.count_documents({}),
            "books": await db.books.count_documents({}),
            "reviews": await db.reviews.count_documents({}),
            "loans": await db.loans.count_documents({}),
            "interactions": {"total": await db.interactions.count_documents({})},
        }

        # Interaction stats per type
        pipeline = [{"$group": {"_id": "$interaction_type", "count": {"$sum": 1}}}]
        interaction_types = await db.interactions.aggregate(pipeline).to_list(length=None)

        for item in interaction_types:
            stats["interactions"][item["_id"]] = item["count"]

        # Active loans
        active_loans = await db.loans.count_documents({"status": "borrowed"})
        stats["active_loans"] = active_loans

        # 🆕 Embedding stats
        embeddings_updated = await db.interactions.count_documents({"embedding_updated": True})
        stats["embeddings"] = {
            "total_interactions": stats["interactions"]["total"],
            "embeddings_updated": embeddings_updated,
            "update_rate": (
                round(embeddings_updated / stats["interactions"]["total"] * 100, 2)
                if stats["interactions"]["total"] > 0
                else 0
            ),
        }

        # Book quality stats
        stats["book_quality"] = {
            "highly_rated": await db.books.count_documents({"average_rating": {"$gte": 4.5}}),
            "hidden_gems": await db.books.count_documents({"average_rating": {"$gte": 4.0}}),
            "total_rated": await db.books.count_documents({"average_rating": {"$gt": 0}}),
        }

        # 🆕 RecommendationService stats
        rec_service = get_recommendation_service()
        if rec_service:
            stats["recommendation_service"] = {
                "loaded": True,
                "total_users_in_model": (
                    len(rec_service.lightgcn.mongo_user_to_idx)
                    if hasattr(rec_service.lightgcn, "mongo_user_to_idx")
                    else 0
                ),
            }

        return stats

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return {"error": "Failed to fetch stats", "details": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
