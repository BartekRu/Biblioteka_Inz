"""
routes/views.py
Views endpoint – rejestruje wyświetlenia książek
"""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from bson import ObjectId

from ..models.dependencies import get_interaction_service
from ..service.interaction_service import InteractionService
from .auth import get_current_user
from ..database import get_database

router = APIRouter()


def to_object_id(id_str: str):
    return ObjectId(id_str) if ObjectId.is_valid(id_str) else id_str


@router.post("/view/{book_id}")
async def register_book_view(
    book_id: str,
    current_user=Depends(get_current_user),
    interaction_service: InteractionService = Depends(get_interaction_service),
):
    """
    Rejestruje wyświetlenie książki (waga 0.3)
    """
    db = get_database()
    user_id = current_user.id

    book_key = to_object_id(book_id)
    book = await db.books.find_one({"_id": book_key})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    interaction_result = await interaction_service.create_interaction(
        user_id=user_id,
        book_id=book_id,
        interaction_type="view",
        metadata={
            "title": book.get("title", "Unknown"),
            "viewed_at": datetime.utcnow().isoformat(),
        },
        update_embedding=True,
    )

    return {
        "message": "View registered",
        "interaction_weight": 0.3,
        "embedding_updated": interaction_result.get("embedding_updated", False),
    }


@router.get("/recent-views")
async def get_recent_views(
    current_user=Depends(get_current_user),
    limit: int = 20,
):
    """Ostatnio oglądane książki"""
    db = get_database()
    user_id = current_user.id

    interactions = (
        await db.interactions.find({"user_id": user_id, "interaction_type": "view"})
        .sort("created_at", -1)
        .limit(limit)
        .to_list(length=limit)
    )

    viewed_books = []
    for inter in interactions:
        book_key = to_object_id(inter["book_id"])
        book = await db.books.find_one({"_id": book_key})
        if book:
            viewed_books.append(
                {
                    "book_id": str(book["_id"]),
                    "title": book.get("title"),
                    "authors": book.get("authors"),
                    "image_url": book.get("image_url"),
                    "viewed_at": inter["created_at"],
                }
            )

    return viewed_books
