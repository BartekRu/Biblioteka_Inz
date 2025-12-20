from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import connect_to_mongo, close_mongo_connection, get_database
from .routes import auth, books, users, loans, reviews, recommendations

# Import dla serwisu rekomendacji
from recommendation_engine.goodbooks_lightgcn_service import get_service
import recommendation_engine.goodbooks_lightgcn_service as service_module


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager - łączy obie funkcjonalności:
    1. Połączenie z MongoDB
    2. Inicjalizacja serwisu rekomendacji
    """
    print("🚀 Starting FastAPI application...")

    # 1. Połącz z MongoDB (twoja stara funkcja)
    await connect_to_mongo()

    # 2. Pobierz database handle
    db = get_database()

    # 3. Inicjalizuj serwis rekomendacji (nowa funkcja)
    print("📊 Initializing recommendation service...")
    service = get_service(db=db)
    service_module.goodbooks_lgcn_service = service
    print("✅ Recommendation service ready!")

    yield

    # Shutdown
    print("👋 Shutting down...")
    await close_mongo_connection()


# Aplikacja FastAPI
app = FastAPI(
    title="Library Management System API",
    description="API dla systemu zarządzania biblioteką z rekomendacjami AI",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rejestracja routerów
app.include_router(auth.router, prefix="/v1/auth", tags=["Authentication"])
app.include_router(books.router, prefix="/v1/books", tags=["Books"])
app.include_router(users.router, prefix="/v1/users", tags=["Users"])
app.include_router(loans.router, prefix="/v1/loans", tags=["Loans"])
app.include_router(reviews.router, prefix="/v1/reviews", tags=["Reviews"])
app.include_router(recommendations.router, tags=["Recommendations"])


@app.get("/")
async def root():
    return {"message": "Library Management System API", "docs": "/docs", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
