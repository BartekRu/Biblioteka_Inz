from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from pydantic import BaseModel

from ..database import get_database
from ..models.user import UserInDB, UserResponse, UserUpdate
from ..routes.auth import get_current_active_user
from recommendation_engine.service import get_recommendations_for_goodbooks_user

router = APIRouter()


# ============================================
# GET /me
# ============================================
@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: UserInDB = Depends(get_current_active_user),
) -> UserResponse:
    user_dict = current_user.model_dump()
    user_dict["_id"] = str(user_dict.pop("id"))
    return UserResponse(**user_dict)


# ============================================
# PATCH /me
# ============================================
@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    user_update: UserUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
) -> UserResponse:
    db = get_database()

    update_data = {
        k: v
        for k, v in user_update.model_dump(exclude_unset=True).items()
        if v is not None
    }

    if not update_data:
        user_dict = current_user.model_dump()
        user_dict["_id"] = str(user_dict.pop("id"))
        return UserResponse(**user_dict)

    update_data["updated_at"] = datetime.utcnow()

    result = await db.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": update_data},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    doc = await db.users.find_one({"_id": ObjectId(current_user.id)})
    doc["_id"] = str(doc["_id"])
    return UserResponse(**doc)


# ============================================
# MODEL odpowiedzi Book Recommendation
# ============================================
class RecommendedBook(BaseModel):
    book_id: str
    title: str
    author: str
    average_rating: Optional[float] = None
    score: float


# ============================================
# GET /me/recommendations
# ============================================
@router.get("/me/recommendations", response_model=List[RecommendedBook])
async def get_my_recommendations(
    n: int = 10,
    current_user: UserInDB = Depends(get_current_active_user),
):
    if not current_user.goodbooks_user_id:
        raise HTTPException(
            status_code=400,
            detail="Użytkownik nie ma przypisanego goodbooks_user_id.",
        )

    db = get_database()

    # 1. Pobierz rekomendacje z modelu (LightGCN albo atrapa)
    recs = get_recommendations_for_goodbooks_user(
        user_goodbooks_id=current_user.goodbooks_user_id,
        top_k=n,
    )

    recommended_books = []

    for rec in recs:
        book = await db.books.find_one({"goodbooks_book_id": rec["book_id"]})
        if not book:
            continue

        recommended_books.append(
            RecommendedBook(
                book_id=str(book["_id"]),
                title=book["title"],
                author=book.get("author", ""),
                average_rating=book.get("average_rating", None),
                score=float(rec["score"]),
            )
        )

    return recommended_books
