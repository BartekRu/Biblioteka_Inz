from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import connect_to_mongo, close_mongo_connection

# Import routes
from .routes import auth, books, recommendations, users

app = FastAPI(
    title="Biblioteka API",
    description="API systemu biblioteki miejskiej z systemem rekomendacji książek",
    version="1.0.0",
    docs_url=f"/{settings.API_VERSION}/docs",
    redoc_url=f"/{settings.API_VERSION}/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    await connect_to_mongo()
    print("Application started successfully!")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    await close_mongo_connection()
    print("Application shut down successfully!")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Witaj w API Biblioteki Miejskiej",
        "version": "1.0.0",
        "docs": f"/{settings.API_VERSION}/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


# Include routers
app.include_router(auth.router, prefix=f"/{settings.API_VERSION}/auth", tags=["Authentication"])
app.include_router(books.router, prefix=f"/{settings.API_VERSION}/books", tags=["Books"])
app.include_router(users.router, prefix=f"/{settings.API_VERSION}/users", tags=["Users"],)
app.include_router(recommendations.router)
# app.include_router(users.router, prefix=f"/{settings.API_VERSION}/users", tags=["Users"])
# app.include_router(recommendations.router, prefix=f"/{settings.API_VERSION}/recommendations", tags=["Recommendations"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
