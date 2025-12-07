from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import connect_to_mongo, close_mongo_connection
from .routes import auth, books, users, loans, reviews

# Opcjonalnie: recommendation engine
try:
    from .routes import recommendations
    RECOMMENDATIONS_AVAILABLE = True
except ImportError:
    RECOMMENDATIONS_AVAILABLE = False
    print("⚠️ Recommendations router not available")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(
    title="Library Management System API",
    description="API dla systemu zarządzania biblioteką z rekomendacjami AI",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
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

if RECOMMENDATIONS_AVAILABLE:
    app.include_router(recommendations.router, tags=["Recommendations"])


@app.get("/")
async def root():
    return {
        "message": "Library Management System API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}