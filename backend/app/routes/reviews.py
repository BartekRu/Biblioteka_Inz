"""
routes/reviews.py
Reviews endpoint with automatic interaction creation
"""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from pydantic import BaseModel
from bson import ObjectId

from ..models.dependencies import get_interaction_service
from ..service.interaction_service import InteractionService
from .auth import get_current_user
from ..database import get_database

router = APIRouter()


class ReviewCreate(BaseModel):
    book_id: str
    rating: int
    content: str


def to_object_id(id_str: str):
    return ObjectId(id_str) if ObjectId.is_valid(id_str) else id_str


@router.post("/")
async def create_review(
    payload: ReviewCreate,
    current_user=Depends(get_current_user),
    interaction_service: InteractionService = Depends(get_interaction_service),
):
    db = get_database()
    user_id = current_user.id

    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1–5")

    if len(payload.content) < 10:
        raise HTTPException(status_code=400, detail="Review too short")

    book_key = to_object_id(payload.book_id)
    book = await db.books.find_one({"_id": book_key})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    existing = await db.reviews.find_one(
        {
            "user_id": user_id,
            "book_id": payload.book_id,
        }
    )
    if existing:
        raise HTTPException(status_code=400, detail="You already reviewed this book")

    review_doc = {
        "user_id": user_id,
        "user_name": getattr(current_user, "username", "Unknown"),
        "book_id": payload.book_id,
        "rating": payload.rating,
        "content": payload.content,
        "created_at": datetime.utcnow(),
    }

    result = await db.reviews.insert_one(review_doc)
    review_id = str(result.inserted_id)
    review_doc["_id"] = review_id

    interaction_result = await interaction_service.create_interaction(
        user_id=user_id,
        book_id=payload.book_id,
        interaction_type="review",
        metadata={"rating": payload.rating, "review_id": review_id},
        update_embedding=True,
    )

    return {
        **review_doc,
        "interaction_created": True,
        "embedding_updated": interaction_result.get("embedding_updated", False),
    }


@router.get("/book/{book_id}")
async def get_book_reviews(book_id: str):
    db = get_database()

    reviews = await db.reviews.find({"book_id": book_id}).sort("created_at", -1).to_list(length=100)

    for r in reviews:
        r["_id"] = str(r["_id"])

    return reviews
