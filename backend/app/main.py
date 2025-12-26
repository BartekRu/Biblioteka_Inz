"""
main.py
FastAPI application with InteractionService + LightGCN recommendations + NEW ENDPOINTS v2.0
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# Database
from .database import connect_to_mongo, close_mongo_connection, get_database

# Routes - ✅ POPRAWIONE IMPORTY
from .routes import auth, books, users, loans, reviews, views
from .routes.recommendations import router as recommendations_router  # ← FIX!

# Recommendation service (twój istniejący LightGCN)
from recommendation_engine.goodbooks_lightgcn_service import get_service
import recommendation_engine.goodbooks_lightgcn_service as service_module

# Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager:
    1. Połączenie z MongoDB
    2. Inicjalizacja serwisu rekomendacji LightGCN
    3. Przygotowanie InteractionService (automatycznie przez DI)
    """
    logger.info("🚀 Starting FastAPI application v2.0...")

    # 1. Połącz z MongoDB
    await connect_to_mongo()
    logger.info("✅ Connected to MongoDB")

    # 2. Pobierz database handle
    db = get_database()

    # 3. Inicjalizuj serwis rekomendacji LightGCN
    logger.info("📊 Initializing LightGCN recommendation service...")
    try:
        service = get_service(db=db)
        service_module.goodbooks_lgcn_service = service
        logger.info("✅ LightGCN service ready!")

        # 4. Wyświetl statystyki interakcji
        interactions_count = await db.interactions.count_documents({})
        logger.info(f"📊 Total interactions in DB: {interactions_count}")

        # Statystyki per typ
        pipeline = [{"$group": {"_id": "$interaction_type", "count": {"$sum": 1}}}]
        stats = await db.interactions.aggregate(pipeline).to_list(length=None)
        for stat in stats:
            logger.info(f"   - {stat['_id']}: {stat['count']}")

    except Exception as e:
        logger.error(f"❌ Failed to initialize recommendation service: {str(e)}")
        logger.warning("⚠️  Continuing without recommendations...")

    logger.info("✅ Application startup complete")
    logger.info("📚 NEW: Hidden Gems & Highly Rated endpoints available!")

    yield

    # Shutdown
    logger.info("👋 Shutting down...")
    await close_mongo_connection()
    logger.info("✅ MongoDB connection closed")


# Aplikacja FastAPI
app = FastAPI(
    title="Biblioteka_Inz API",
    description="AI-powered library management system with LightGCN recommendations, InteractionService, and Advanced Discovery (Hidden Gems, Highly Rated)",
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
# Rejestracja routerów - ✅ POPRAWIONE
# ============================================================================

# Core routes
app.include_router(auth.router, prefix="/v1/auth", tags=["Authentication"])
app.include_router(books.router, prefix="/v1/books", tags=["Books"])
app.include_router(users.router, prefix="/v1/users", tags=["Users"])
app.include_router(loans.router, prefix="/v1/loans", tags=["Loans"])
app.include_router(reviews.router, prefix="/v1/reviews", tags=["Reviews"])
app.include_router(views.router, prefix="/v1/views", tags=["Views"])

# Recommendations routes - ✅ POPRAWIONE (było: recommendation.router)
app.include_router(recommendations_router, prefix="/v1/recommendations", tags=["Recommendations"])


@app.get("/")
async def root():
    """Root endpoint z informacjami o API"""
    return {
        "message": "Biblioteka_Inz API",
        "version": "2.0.0",
        "features": [
            "InteractionService (view, borrow, review)",
            "LightGCN recommendations with MMR",
            "Real-time embedding updates",
            "Loan history integration (borrow weight: 1.0)",
            "🆕 Hidden Gems discovery (underrated books)",
            "🆕 Highly Rated recommendations (quality guarantee)",
            "🆕 Genre & Author personalization",
            "🆕 Similar Readers collaborative filtering",
        ],
        "docs": "/docs",
        "redoc": "/redoc",
        "new_endpoints": [
            "/v1/recommendations/hidden-gems",
            "/v1/recommendations/highly-rated",
            "/v1/recommendations/by-genre",
            "/v1/recommendations/by-author",
            "/v1/recommendations/similar-readers",
            "/v1/recommendations/new-arrivals",
        ],
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db = get_database()

    # Sprawdź połączenie z MongoDB
    try:
        await db.command("ping")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "unhealthy"

    # Sprawdź serwis rekomendacji
    rec_service_status = (
        "healthy" if hasattr(service_module, "goodbooks_lgcn_service") else "not_initialized"
    )

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "recommendation_service": rec_service_status,
        "version": "2.0.0",
        "new_features": ["hidden_gems", "highly_rated", "genre_recs", "author_recs"],
    }


@app.get("/v1/stats")
async def get_stats():
    """
    Statystyki systemu
    Pokazuje liczbę interakcji (view, review, borrow), użytkowników, książek
    """
    db = get_database()

    try:
        # Statystyki podstawowe
        stats = {
            "users": await db.users.count_documents({}),
            "books": await db.books.count_documents({}),
            "reviews": await db.reviews.count_documents({}),
            "loans": await db.loans.count_documents({}),
            "interactions": {"total": await db.interactions.count_documents({})},
        }

        # Statystyki interakcji per typ (view, review, borrow)
        pipeline = [{"$group": {"_id": "$interaction_type", "count": {"$sum": 1}}}]
        interaction_types = await db.interactions.aggregate(pipeline).to_list(length=None)

        for item in interaction_types:
            stats["interactions"][item["_id"]] = item["count"]

        # Statystyki wypożyczeń
        active_loans = await db.loans.count_documents({"status": "borrowed"})
        stats["active_loans"] = active_loans

        # 🆕 NEW: Statystyki dla nowych endpointów
        stats["book_quality"] = {
            "highly_rated": await db.books.count_documents({"average_rating": {"$gte": 4.5}}),
            "hidden_gems": await db.books.count_documents({"average_rating": {"$gte": 4.0}}),
            "total_rated": await db.books.count_documents({"average_rating": {"$gt": 0}}),
        }

        return stats

    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        return {"error": "Failed to fetch stats"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
