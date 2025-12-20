"""
reviews.py - ZAKTUALIZOWANE z automatycznym tworzeniem interakcji

ZMIANY:
- Po utworzeniu recenzji automatycznie tworzy interakcję typu 'review'
- Interakcja jest zapisywana do kolekcji 'interactions'
- Wywoływany jest endpoint rekomendacji do aktualizacji embeddingów
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime

from ..database import get_database
from ..routes.auth import get_current_active_user
from ..models.user import UserInDB
from ..models.interaction import InteractionCreate, get_interaction_weight

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
# 🆕 HELPER: Utwórz interakcję po recenzji
# ============================================
async def create_review_interaction(
    db,
    user_id: str,
    book_id: str,
    rating: int
):
    """
    Tworzy interakcję typu 'review' w kolekcji interactions.
    
    Ta funkcja jest wywoływana automatycznie po dodaniu/edycji recenzji.
    """
    try:
        # Przygotuj dokument interakcji
        interaction_doc = {
            "user_id": user_id,
            "book_id": book_id,
            "interaction_type": "review",
            "rating": rating,
            "weight": get_interaction_weight("review"),  # 0.8
            "timestamp": datetime.utcnow(),
            "metadata": {
                "source": "review_endpoint",
                "auto_created": True
            }
        }
        
        # Zapisz do kolekcji interactions
        result = await db.interactions.insert_one(interaction_doc)
        
        print(f"✅ Utworzono interakcję review: user={user_id[:12]}, book={book_id[:12]}")
        
        return result.inserted_id
        
    except Exception as e:
        print(f"❌ Błąd przy tworzeniu interakcji: {e}")
        # Nie rzucamy wyjątku - recenzja powinna zostać zapisana nawet jeśli interakcja nie
        return None


# ============================================
# 🆕 HELPER: Wyślij do systemu rekomendacji
# ============================================
async def trigger_recommendation_update(
    user_id: str,
    book_id: str,
    interaction_type: str = "review"
):
    """
    Wywołaj endpoint rekomendacji aby zaktualizować embeddingi użytkownika.
    
    Używa importu lokalnego aby uniknąć circular imports.
    """
    try:
        from recommendation_engine.goodbooks_lightgcn_service import goodbooks_lgcn_service
        
        # Pobierz goodbooks_book_id
        db = get_database()
        book = await db.books.find_one({"_id": ObjectId(book_id)})
        
        if not book:
            print(f"⚠️  Nie znaleziono książki {book_id}")
            return None
        
        goodbooks_id = book.get("goodbooks_book_id")
        if not goodbooks_id:
            print(f"⚠️  Książka {book_id} nie ma goodbooks_book_id")
            return None
        
        # Wywołaj process_interaction
        update_result = goodbooks_lgcn_service.process_interaction(
            mongo_user_id=user_id,
            goodbooks_book_id=int(goodbooks_id),
            interaction_type=interaction_type
        )
        
        if update_result.get("success"):
            print(f"✅ Zaktualizowano embeddingi użytkownika: {user_id[:12]}")
        else:
            print(f"⚠️  Nie udało się zaktualizować embeddingów: {update_result.get('reason')}")
        
        return update_result
        
    except Exception as e:
        print(f"❌ Błąd przy aktualizacji embeddingów: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================
# POST /reviews/ - Dodaj recenzję - ZAKTUALIZOWANE
# ============================================
@router.post("/", status_code=201)
async def create_review(
    review_data: ReviewCreate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Dodaj nową recenzję książki.
    
    🆕 NOWE: Automatycznie tworzy interakcję i aktualizuje embeddingi!
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
    
    # 🆕 KLUCZOWA ZMIANA: Utwórz interakcję
    interaction_id = await create_review_interaction(
        db=db,
        user_id=current_user.id,
        book_id=review_data.book_id,
        rating=review_data.rating
    )
    
    # 🆕 KLUCZOWA ZMIANA: Zaktualizuj embeddingi
    update_result = await trigger_recommendation_update(
        user_id=current_user.id,
        book_id=review_data.book_id,
        interaction_type="review"
    )
    
    # Pobierz utworzoną recenzję
    created_review = await db.reviews.find_one({"_id": result.inserted_id})
    created_review["_id"] = str(created_review["_id"])
    created_review["username"] = current_user.username if hasattr(current_user, 'username') else ""
    created_review["user_name"] = current_user.full_name
    
    # 🆕 Dodaj info o interakcji do odpowiedzi
    created_review["interaction_created"] = interaction_id is not None
    created_review["embedding_updated"] = update_result.get("success", False) if update_result else False
    
    return created_review


# ============================================
# PUT /reviews/{id} - Aktualizuj recenzję - ZAKTUALIZOWANE
# ============================================
@router.put("/{review_id}")
async def update_review(
    review_id: str,
    review_data: ReviewUpdate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Aktualizuj swoją recenzję.
    
    🆕 NOWE: Jeśli zmienia się ocena, aktualizuje też interakcję!
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
    rating_changed = False
    
    if review_data.rating is not None:
        update_data["rating"] = review_data.rating
        rating_changed = (review_data.rating != review.get("rating"))
    
    if review_data.content is not None:
        update_data["content"] = review_data.content
    
    await db.reviews.update_one(
        {"_id": ObjectId(review_id)},
        {"$set": update_data}
    )
    
    # Aktualizuj średnią ocenę książki
    await update_book_rating(db, review["book_id"])
    
    # 🆕 Jeśli zmieniono ocenę, zaktualizuj interakcję i embeddingi
    if rating_changed and review_data.rating is not None:
        # Zaktualizuj istniejącą interakcję lub utwórz nową
        existing_interaction = await db.interactions.find_one({
            "user_id": current_user.id,
            "book_id": review["book_id"],
            "interaction_type": "review"
        })
        
        if existing_interaction:
            # Aktualizuj istniejącą
            await db.interactions.update_one(
                {"_id": existing_interaction["_id"]},
                {"$set": {
                    "rating": review_data.rating,
                    "timestamp": datetime.utcnow()
                }}
            )
            print(f"✅ Zaktualizowano interakcję review")
        else:
            # Utwórz nową
            await create_review_interaction(
                db=db,
                user_id=current_user.id,
                book_id=review["book_id"],
                rating=review_data.rating
            )
        
        # Zaktualizuj embeddingi
        await trigger_recommendation_update(
            user_id=current_user.id,
            book_id=review["book_id"],
            interaction_type="review"
        )
    
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
    
    🆕 UWAGA: Nie usuwa interakcji - zachowujemy historię dla modelu
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
    
    # 🆕 UWAGA: Celowo NIE usuwamy interakcji
    # Model ML powinien zachować historyczną wiedzę o preferencjach
    # Możemy dodać flagę 'deleted' jeśli potrzeba
    
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