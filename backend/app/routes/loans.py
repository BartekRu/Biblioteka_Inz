from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta

from ..database import get_database
from ..routes.auth import get_current_active_user
from ..models.user import UserInDB

router = APIRouter()



class LoanCreate(BaseModel):
    book_id: str
    librarian_notes: Optional[str] = None


class LoanReturn(BaseModel):
    librarian_notes: Optional[str] = None



@router.get("/")
async def get_loans(
    status: Optional[str] = Query(None, description="active, returned, overdue"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Pobierz listę wypożyczeń (wymaga roli admin lub librarian).
    """
    if current_user.role not in ["admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    
    db = get_database()
    
    query = {}
    if status:
        query["status"] = status
    
    skip = (page - 1) * limit
    
    cursor = db.loans.find(query).sort("loan_date", -1).skip(skip).limit(limit)
    
    loans = []
    async for loan in cursor:
        loan["_id"] = str(loan["_id"])
        
        if loan.get("book_id"):
            try:
                book = await db.books.find_one({"_id": ObjectId(loan["book_id"])})
                if book:
                    loan["book_title"] = book.get("title", "")
                    loan["book_author"] = book.get("author", "")
            except:
                pass
        
        if loan.get("user_id"):
            try:
                user = await db.users.find_one({"_id": ObjectId(loan["user_id"])})
                if user:
                    loan["username"] = user.get("username", "")
                    loan["user_name"] = user.get("full_name", "")
            except:
                pass
        
        if loan["status"] == "active" and loan.get("due_date"):
            loan["is_overdue"] = datetime.utcnow() > loan["due_date"]
        else:
            loan["is_overdue"] = False
        
        loans.append(loan)
    
    total = await db.loans.count_documents(query)
    
    return {
        "loans": loans,
        "total": total,
        "page": page,
        "limit": limit
    }


@router.get("/me")
async def get_my_loans(
    status: Optional[str] = Query(None),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Pobierz wypożyczenia zalogowanego użytkownika.
    """
    db = get_database()
    
    query = {"user_id": current_user.id}
    if status:
        query["status"] = status
    
    cursor = db.loans.find(query).sort("loan_date", -1)
    
    loans = []
    async for loan in cursor:
        loan["_id"] = str(loan["_id"])
        
        if loan.get("book_id"):
            try:
                book = await db.books.find_one({"_id": ObjectId(loan["book_id"])})
                if book:
                    loan["book_title"] = book.get("title", "")
                    loan["book_author"] = book.get("author", "")
                    loan["book_image"] = book.get("image_url") or book.get("cover_image")
            except:
                pass
        
        if loan["status"] == "active" and loan.get("due_date"):
            loan["is_overdue"] = datetime.utcnow() > loan["due_date"]
        else:
            loan["is_overdue"] = False
        
        loans.append(loan)
    
    return loans



@router.get("/{loan_id}")
async def get_loan(
    loan_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Pobierz szczegóły wypożyczenia.
    """
    db = get_database()
    
    if not ObjectId.is_valid(loan_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID wypożyczenia")
    
    loan = await db.loans.find_one({"_id": ObjectId(loan_id)})
    
    if not loan:
        raise HTTPException(status_code=404, detail="Wypożyczenie nie znalezione")
    
    if loan["user_id"] != current_user.id and current_user.role not in ["admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    
    loan["_id"] = str(loan["_id"])
    
    return loan


@router.post("/", status_code=201)
async def create_loan(
    loan_data: LoanCreate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Wypożycz książkę.
    """
    db = get_database()
    
    if not ObjectId.is_valid(loan_data.book_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID książki")
    
    book = await db.books.find_one({"_id": ObjectId(loan_data.book_id)})
    
    if not book:
        raise HTTPException(status_code=404, detail="Książka nie znaleziona")
    
    if book.get("available_copies", 0) <= 0:
        raise HTTPException(status_code=400, detail="Brak dostępnych egzemplarzy")
    
    existing_loan = await db.loans.find_one({
        "book_id": loan_data.book_id,
        "user_id": current_user.id,
        "status": "active"
    })
    
    if existing_loan:
        raise HTTPException(status_code=400, detail="Masz już wypożyczoną tę książkę")
    
    active_loans_count = await db.loans.count_documents({
        "user_id": current_user.id,
        "status": "active"
    })
    
    if active_loans_count >= 5:
        raise HTTPException(
            status_code=400, 
            detail="Osiągnięto limit wypożyczeń (max 5 książek jednocześnie)"
        )
    
    loan_doc = {
        "book_id": loan_data.book_id,
        "user_id": current_user.id,
        "loan_date": datetime.utcnow(),
        "due_date": datetime.utcnow() + timedelta(days=30),
        "return_date": None,
        "status": "active",
        "renewal_count": 0,
        "max_renewals": 2,
        "librarian_notes": loan_data.librarian_notes
    }
    
    result = await db.loans.insert_one(loan_doc)
    
    await db.books.update_one(
        {"_id": ObjectId(loan_data.book_id)},
        {
            "$inc": {"available_copies": -1, "total_loans": 1},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    await db.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {
            "$addToSet": {"reading_history": loan_data.book_id},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    created_loan = await db.loans.find_one({"_id": result.inserted_id})
    created_loan["_id"] = str(created_loan["_id"])
    created_loan["book_title"] = book.get("title", "")
    
    return created_loan



@router.post("/{loan_id}/return")
async def return_loan(
    loan_id: str,
    return_data: LoanReturn = LoanReturn(),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Zwróć wypożyczoną książkę.
    """
    db = get_database()
    
    if not ObjectId.is_valid(loan_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID wypożyczenia")
    
    loan = await db.loans.find_one({"_id": ObjectId(loan_id)})
    
    if not loan:
        raise HTTPException(status_code=404, detail="Wypożyczenie nie znalezione")
    
    if loan["user_id"] != current_user.id and current_user.role not in ["admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    
    if loan["status"] != "active":
        raise HTTPException(status_code=400, detail="To wypożyczenie nie jest aktywne")
    
    await db.loans.update_one(
        {"_id": ObjectId(loan_id)},
        {"$set": {
            "status": "returned",
            "return_date": datetime.utcnow(),
            "librarian_notes": return_data.librarian_notes or loan.get("librarian_notes")
        }}
    )
    
    await db.books.update_one(
        {"_id": ObjectId(loan["book_id"])},
        {
            "$inc": {"available_copies": 1},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return {"message": "Książka została zwrócona"}



@router.post("/{loan_id}/renew")
async def renew_loan(
    loan_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Przedłuż wypożyczenie o 14 dni (max 2 przedłużenia).
    """
    db = get_database()
    
    if not ObjectId.is_valid(loan_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID wypożyczenia")
    
    loan = await db.loans.find_one({"_id": ObjectId(loan_id)})
    
    if not loan:
        raise HTTPException(status_code=404, detail="Wypożyczenie nie znalezione")
    
    if loan["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    
    if loan["status"] != "active":
        raise HTTPException(status_code=400, detail="To wypożyczenie nie jest aktywne")
    
    if loan.get("renewal_count", 0) >= loan.get("max_renewals", 2):
        raise HTTPException(
            status_code=400, 
            detail="Osiągnięto maksymalną liczbę przedłużeń"
        )
    
    new_due_date = loan["due_date"] + timedelta(days=14)
    
    await db.loans.update_one(
        {"_id": ObjectId(loan_id)},
        {"$set": {
            "due_date": new_due_date
        }, "$inc": {
            "renewal_count": 1
        }}
    )
    
    return {
        "message": "Wypożyczenie przedłużone o 14 dni",
        "new_due_date": new_due_date.isoformat()
    }



@router.get("/can-borrow/{book_id}")
async def can_borrow_book(
    book_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Sprawdź czy użytkownik może wypożyczyć daną książkę.
    """
    db = get_database()
    
    if not ObjectId.is_valid(book_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID książki")
    
    book = await db.books.find_one({"_id": ObjectId(book_id)})
    
    if not book:
        return {"can_borrow": False, "reason": "Książka nie istnieje"}
    
    if book.get("available_copies", 0) <= 0:
        return {"can_borrow": False, "reason": "Brak dostępnych egzemplarzy"}
    
    existing = await db.loans.find_one({
        "book_id": book_id,
        "user_id": current_user.id,
        "status": "active"
    })
    
    if existing:
        return {"can_borrow": False, "reason": "Masz już wypożyczoną tę książkę"}
    
    active_count = await db.loans.count_documents({
        "user_id": current_user.id,
        "status": "active"
    })
    
    if active_count >= 5:
        return {"can_borrow": False, "reason": "Osiągnięto limit 5 wypożyczeń"}
    
    return {"can_borrow": True, "reason": None}