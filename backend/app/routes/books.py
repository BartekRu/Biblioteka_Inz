from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from bson import ObjectId
from datetime import datetime
import math

from ..database import get_database
from ..routes.auth import get_current_active_user, get_current_user
from ..models.user import UserInDB

router = APIRouter()


# ============================================
# GET /books/ - Lista książek z paginacją
# ============================================
@router.get("/")
async def get_books(
    page: int = Query(1, ge=1, description="Numer strony"),
    limit: int = Query(12, ge=1, le=100, description="Liczba książek na stronę"),
    search: Optional[str] = Query(None, description="Szukaj po tytule lub autorze"),
    genre: Optional[str] = Query(None, description="Filtruj po gatunku"),
    sort: str = Query("title", description="Sortowanie: title, -title, -average_rating, -ratings_count, publication_year, -publication_year"),
    available_only: bool = Query(False, description="Tylko dostępne")
):
    """
    Pobierz listę książek z paginacją, wyszukiwaniem i filtrami.
    """
    db = get_database()
    
    # Buduj query
    query = {}
    
    # Wyszukiwanie tekstowe
    if search:
        # Użyj text search jeśli dostępny, w przeciwnym razie regex
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"author": {"$regex": search, "$options": "i"}}
        ]
    
    # Filtr gatunku
    if genre:
        query["genre"] = {"$regex": genre, "$options": "i"}
    
    # Tylko dostępne
    if available_only:
        query["available_copies"] = {"$gt": 0}
    
    # Sortowanie
    sort_field = sort.lstrip("-")
    sort_order = -1 if sort.startswith("-") else 1
    
    # Mapowanie pól sortowania
    sort_mapping = {
        "title": "title",
        "author": "author",
        "average_rating": "average_rating",
        "ratings_count": "ratings_count",
        "publication_year": "publication_year",
        "created_at": "created_at"
    }
    sort_field = sort_mapping.get(sort_field, "title")
    
    # Policz całkowitą liczbę
    total = await db.books.count_documents(query)
    total_pages = math.ceil(total / limit) if total > 0 else 1
    
    # Pobierz książki
    skip = (page - 1) * limit
    cursor = db.books.find(query).sort(sort_field, sort_order).skip(skip).limit(limit)
    
    books = []
    async for book in cursor:
        book["_id"] = str(book["_id"])
        books.append(book)
    
    return {
        "books": books,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }


# ============================================
# GET /books/{id} - Szczegóły książki
# ============================================
@router.get("/{book_id}")
async def get_book(book_id: str):
    """
    Pobierz szczegóły pojedynczej książki.
    """
    db = get_database()
    
    if not ObjectId.is_valid(book_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID książki")
    
    book = await db.books.find_one({"_id": ObjectId(book_id)})
    
    if not book:
        raise HTTPException(status_code=404, detail="Książka nie znaleziona")
    
    book["_id"] = str(book["_id"])
    return book


# ============================================
# POST /books/ - Dodaj książkę (admin/librarian)
# ============================================
@router.post("/", status_code=201)
async def create_book(
    book_data: dict,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Dodaj nową książkę (wymaga roli admin lub librarian).
    """
    if current_user.role not in ["admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    
    db = get_database()
    
    # Ustaw domyślne wartości
    book_data["created_at"] = datetime.utcnow()
    book_data["updated_at"] = datetime.utcnow()
    book_data.setdefault("available_copies", book_data.get("total_copies", 1))
    book_data.setdefault("average_rating", 0)
    book_data.setdefault("ratings_count", 0)
    book_data.setdefault("total_loans", 0)
    
    result = await db.books.insert_one(book_data)
    
    created_book = await db.books.find_one({"_id": result.inserted_id})
    created_book["_id"] = str(created_book["_id"])
    
    return created_book


# ============================================
# PUT /books/{id} - Aktualizuj książkę
# ============================================
@router.put("/{book_id}")
async def update_book(
    book_id: str,
    book_data: dict,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Aktualizuj książkę (wymaga roli admin lub librarian).
    """
    if current_user.role not in ["admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    
    db = get_database()
    
    if not ObjectId.is_valid(book_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID książki")
    
    book_data["updated_at"] = datetime.utcnow()
    
    # Usuń _id jeśli został przesłany
    book_data.pop("_id", None)
    
    result = await db.books.update_one(
        {"_id": ObjectId(book_id)},
        {"$set": book_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Książka nie znaleziona")
    
    updated_book = await db.books.find_one({"_id": ObjectId(book_id)})
    updated_book["_id"] = str(updated_book["_id"])
    
    return updated_book


# ============================================
# DELETE /books/{id} - Usuń książkę
# ============================================
@router.delete("/{book_id}")
async def delete_book(
    book_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Usuń książkę (wymaga roli admin).
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    
    db = get_database()
    
    if not ObjectId.is_valid(book_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID książki")
    
    # Sprawdź czy książka nie jest wypożyczona
    active_loan = await db.loans.find_one({
        "book_id": book_id,
        "status": "active"
    })
    
    if active_loan:
        raise HTTPException(
            status_code=400, 
            detail="Nie można usunąć książki - jest aktualnie wypożyczona"
        )
    
    result = await db.books.delete_one({"_id": ObjectId(book_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Książka nie znaleziona")
    
    return {"message": "Książka została usunięta"}


# ============================================
# GET /books/{id}/similar - Podobne książki
# ============================================
@router.get("/{book_id}/similar")
async def get_similar_books(
    book_id: str,
    limit: int = Query(6, ge=1, le=20)
):
    """
    Pobierz podobne książki (na podstawie gatunku i autora).
    """
    db = get_database()
    
    if not ObjectId.is_valid(book_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID książki")
    
    book = await db.books.find_one({"_id": ObjectId(book_id)})
    
    if not book:
        raise HTTPException(status_code=404, detail="Książka nie znaleziona")
    
    # Znajdź podobne po gatunku lub autorze
    query = {
        "_id": {"$ne": ObjectId(book_id)},
        "$or": []
    }
    
    if book.get("genre"):
        query["$or"].append({"genre": {"$in": book["genre"]}})
    
    if book.get("author"):
        query["$or"].append({"author": book["author"]})
    
    if not query["$or"]:
        return []
    
    cursor = db.books.find(query).sort("average_rating", -1).limit(limit)
    
    similar = []
    async for similar_book in cursor:
        similar_book["_id"] = str(similar_book["_id"])
        similar.append(similar_book)
    
    return similar