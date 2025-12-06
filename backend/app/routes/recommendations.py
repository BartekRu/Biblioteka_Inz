from fastapi import APIRouter, HTTPException
from typing import List, Optional

# Import serwisu
import sys
sys.path.append(".")
from recommendation_engine.recommender_service import get_recommender

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


@router.get("/user/{user_id}")
async def get_user_recommendations(
    user_id: int, 
    n: int = 10,
    exclude: Optional[str] = None  # comma-separated book IDs
):
    """
    Rekomendacje dla użytkownika
    
    - user_id: ID użytkownika z goodbooks-10k (1-53424)
    - n: liczba rekomendacji
    - exclude: książki do wykluczenia (np. już przeczytane)
    """
    try:
        recommender = get_recommender()
        
        # Mapuj user_id na indeks
        user_idx = recommender.user_mapping['to_idx'].get(str(user_id))
        if user_idx is None:
            raise HTTPException(404, f"Użytkownik {user_id} nie istnieje w modelu")
        
        # Parsuj exclude
        exclude_indices = []
        if exclude:
            for book_id in exclude.split(','):
                book_idx = recommender.book_mapping['to_idx'].get(book_id.strip())
                if book_idx:
                    exclude_indices.append(book_idx)
        
        recs = recommender.get_recommendations(user_idx, n, exclude_indices)
        
        return {
            "user_id": user_id,
            "recommendations": recs
        }
        
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/similar/{book_id}")
async def get_similar_books(book_id: int, n: int = 10):
    """
    Książki podobne do podanej
    
    - book_id: ID książki z goodbooks-10k (1-10000)
    - n: liczba podobnych
    """
    try:
        recommender = get_recommender()
        
        book_idx = recommender.book_mapping['to_idx'].get(str(book_id))
        if book_idx is None:
            raise HTTPException(404, f"Książka {book_id} nie istnieje w modelu")
        
        similar = recommender.get_similar_books(book_idx, n)
        
        return {
            "book_id": book_id,
            "similar_books": similar
        }
        
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/health")
async def health_check():
    """Sprawdź czy model jest załadowany"""
    try:
        recommender = get_recommender()
        return {
            "status": "ok",
            "model_loaded": recommender.is_loaded,
            "n_users": recommender.user_embeddings.shape[0],
            "n_books": recommender.item_embeddings.shape[0]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}