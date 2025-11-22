from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime
from ..models.book import Book, BookCreate, BookUpdate, BookResponse
from ..models.user import UserInDB
from ..routes.auth import get_current_active_user
from ..database import get_database
from bson import ObjectId

router = APIRouter()


@router.get("/", response_model=List[BookResponse])
async def get_books(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    genre: Optional[str] = None,
    author: Optional[str] = None
):
    """Get all books with optional filters"""
    db = get_database()
    
    # Build query
    query = {}
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"author": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    if genre:
        query["genre"] = {"$regex": genre, "$options": "i"}
    if author:
        query["author"] = {"$regex": author, "$options": "i"}
    
    # Get books
    cursor = db.books.find(query).skip(skip).limit(limit)
    books = await cursor.to_list(length=limit)
    
    # Convert ObjectId to string
    for book in books:
        book["_id"] = str(book["_id"])
    
    return [BookResponse(**book) for book in books]


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: str):
    """Get a specific book by ID"""
    db = get_database()
    
    try:
        book = await db.books.find_one({"_id": ObjectId(book_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid book ID format"
        )
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    book["_id"] = str(book["_id"])
    return BookResponse(**book)


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    book: BookCreate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Create a new book (librarian/admin only)"""
    if current_user.role not in ["librarian", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    db = get_database()
    
    # Create book
    book_dict = book.model_dump()
    book_dict["created_at"] = datetime.utcnow()
    book_dict["updated_at"] = datetime.utcnow()
    book_dict["added_by"] = str(current_user.id)
    book_dict["total_loans"] = 0
    book_dict["total_reviews"] = 0
    book_dict["average_rating"] = 0.0
    
    result = await db.books.insert_one(book_dict)
    created_book = await db.books.find_one({"_id": result.inserted_id})
    
    created_book["_id"] = str(created_book["_id"])
    return BookResponse(**created_book)


@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: str,
    book_update: BookUpdate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Update a book (librarian/admin only)"""
    if current_user.role not in ["librarian", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    db = get_database()
    
    # Check if book exists
    try:
        existing_book = await db.books.find_one({"_id": ObjectId(book_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid book ID format"
        )
    
    if not existing_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    # Update book
    update_data = {k: v for k, v in book_update.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    await db.books.update_one(
        {"_id": ObjectId(book_id)},
        {"$set": update_data}
    )
    
    updated_book = await db.books.find_one({"_id": ObjectId(book_id)})
    updated_book["_id"] = str(updated_book["_id"])
    
    return BookResponse(**updated_book)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Delete a book (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    db = get_database()
    
    # Check if book exists
    try:
        book = await db.books.find_one({"_id": ObjectId(book_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid book ID format"
        )
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    # Delete book
    await db.books.delete_one({"_id": ObjectId(book_id)})
    
    return None
