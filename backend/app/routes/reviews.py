from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime

from ..database import get_database
from ..routes.auth import get_current_active_user
from ..models.user import UserInDB

router = APIRouter()


# ============================================
# Modele Pydantic
# ============================================
class ReviewCreate(BaseModel):
    book_id: str
    rating: int = Field(..., ge=1, le=5, description="Ocena 1-5")
    content: Optional[str] = Field(None, max_length=2000, description="Treść recenzji")


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    content: Optional[str] = Field(None, max_length=2000)


class ReviewResponse(BaseModel):
    id: str = Field(alias="_id")
    book_id: str
    user_id: str
    username: Optional[str] = None
    user_name: Optional[str] = None
    rating: int
    content: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True


# ============================================
# GET /reviews/book/{book_id} - Recenzje książki
# ============================================
@router.get("/book/{book_id}")
async def get_book_reviews(
    book_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Pobierz recenzje dla danej książki.
    """
    db = get_database()
    
    if not ObjectId.is_valid(book_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID książki")
    
    skip = (page - 1) * limit
    
    cursor = db.reviews.find({"book_id": book_id}).sort("created_at", -1).skip(skip).limit(limit)
    
    reviews = []
    async for review in cursor:
        review["_id"] = str(review["_id"])
        
        # Pobierz nazwę użytkownika
        if review.get("user_id"):
            try:
                user = await db.users.find_one({"_id": ObjectId(review["user_id"])})
                if user:
                    review["username"] = user.get("username", "")
                    review["user_name"] = user.get("full_name", "")
            except:
                pass
        
        reviews.append(review)
    
    return reviews


# ============================================
# GET /reviews/me - Moje recenzje
# ============================================
@router.get("/me")
async def get_my_reviews(
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Pobierz wszystkie recenzje zalogowanego użytkownika.
    """
    db = get_database()
    
    cursor = db.reviews.find({"user_id": current_user.id}).sort("created_at", -1)
    
    reviews = []
    async for review in cursor:
        review["_id"] = str(review["_id"])
        
        # Pobierz tytuł książki
        if review.get("book_id"):
            try:
                book = await db.books.find_one({"_id": ObjectId(review["book_id"])})
                if book:
                    review["book_title"] = book.get("title", "")
                    review["book_author"] = book.get("author", "")
            except:
                pass
        
        reviews.append(review)
    
    return reviews


# ============================================
# POST /reviews/ - Dodaj recenzję
# ============================================
@router.post("/", status_code=201)
async def create_review(
    review_data: ReviewCreate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Dodaj nową recenzję książki.
    Użytkownik może dodać tylko jedną recenzję do danej książki.
    """
    db = get_database()
    
    # Sprawdź czy książka istnieje
    if not ObjectId.is_valid(review_data.book_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID książki")
    
    book = await db.books.find_one({"_id": ObjectId(review_data.book_id)})
    if not book:
        raise HTTPException(status_code=404, detail="Książka nie znaleziona")
    
    # Sprawdź czy użytkownik już nie dodał recenzji
    existing_review = await db.reviews.find_one({
        "book_id": review_data.book_id,
        "user_id": current_user.id
    })
    
    if existing_review:
        raise HTTPException(
            status_code=400, 
            detail="Już dodałeś recenzję do tej książki. Możesz ją edytować."
        )
    
    # Utwórz recenzję
    review_doc = {
        "book_id": review_data.book_id,
        "user_id": current_user.id,
        "rating": review_data.rating,
        "content": review_data.content,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.reviews.insert_one(review_doc)
    
    # Aktualizuj średnią ocenę książki
    await update_book_rating(db, review_data.book_id)
    
    # Pobierz utworzoną recenzję
    created_review = await db.reviews.find_one({"_id": result.inserted_id})
    created_review["_id"] = str(created_review["_id"])
    created_review["username"] = current_user.username if hasattr(current_user, 'username') else ""
    created_review["user_name"] = current_user.full_name
    
    return created_review


# ============================================
# PUT /reviews/{id} - Aktualizuj recenzję
# ============================================
@router.put("/{review_id}")
async def update_review(
    review_id: str,
    review_data: ReviewUpdate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Aktualizuj swoją recenzję.
    """
    db = get_database()
    
    if not ObjectId.is_valid(review_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID recenzji")
    
    # Znajdź recenzję
    review = await db.reviews.find_one({"_id": ObjectId(review_id)})
    
    if not review:
        raise HTTPException(status_code=404, detail="Recenzja nie znaleziona")
    
    # Sprawdź czy to recenzja użytkownika
    if review["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Możesz edytować tylko swoje recenzje")
    
    # Aktualizuj
    update_data = {"updated_at": datetime.utcnow()}
    if review_data.rating is not None:
        update_data["rating"] = review_data.rating
    if review_data.content is not None:
        update_data["content"] = review_data.content
    
    await db.reviews.update_one(
        {"_id": ObjectId(review_id)},
        {"$set": update_data}
    )
    
    # Aktualizuj średnią ocenę książki
    await update_book_rating(db, review["book_id"])
    
    # Pobierz zaktualizowaną recenzję
    updated_review = await db.reviews.find_one({"_id": ObjectId(review_id)})
    updated_review["_id"] = str(updated_review["_id"])
    
    return updated_review


# ============================================
# DELETE /reviews/{id} - Usuń recenzję
# ============================================
@router.delete("/{review_id}")
async def delete_review(
    review_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Usuń swoją recenzję.
    Admin może usunąć dowolną recenzję.
    """
    db = get_database()
    
    if not ObjectId.is_valid(review_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID recenzji")
    
    # Znajdź recenzję
    review = await db.reviews.find_one({"_id": ObjectId(review_id)})
    
    if not review:
        raise HTTPException(status_code=404, detail="Recenzja nie znaleziona")
    
    # Sprawdź uprawnienia
    if review["user_id"] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Brak uprawnień do usunięcia tej recenzji")
    
    book_id = review["book_id"]
    
    # Usuń recenzję
    await db.reviews.delete_one({"_id": ObjectId(review_id)})
    
    # Aktualizuj średnią ocenę książki
    await update_book_rating(db, book_id)
    
    return {"message": "Recenzja została usunięta"}


# ============================================
# Helper: Aktualizuj średnią ocenę książki
# ============================================
async def update_book_rating(db, book_id: str):
    """
    Przelicz i zaktualizuj średnią ocenę książki na podstawie recenzji.
    """
    pipeline = [
        {"$match": {"book_id": book_id}},
        {"$group": {
            "_id": "$book_id",
            "average_rating": {"$avg": "$rating"},
            "ratings_count": {"$sum": 1}
        }}
    ]
    
    cursor = db.reviews.aggregate(pipeline)
    result = await cursor.to_list(length=1)
    
    if result:
        stats = result[0]
        await db.books.update_one(
            {"_id": ObjectId(book_id)},
            {"$set": {
                "average_rating": round(stats["average_rating"], 2),
                "ratings_count": stats["ratings_count"],
                "updated_at": datetime.utcnow()
            }}
        )
    else:
        # Brak recenzji - resetuj oceny
        await db.books.update_one(
            {"_id": ObjectId(book_id)},
            {"$set": {
                "average_rating": 0,
                "ratings_count": 0,
                "updated_at": datetime.utcnow()
            }}
        )