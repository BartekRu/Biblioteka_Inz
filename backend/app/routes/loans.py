from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from bson import ObjectId
from datetime import datetime, timedelta

from ..database import get_database
from ..routes.auth import get_current_active_user
from ..models.user import UserInDB
from pydantic import BaseModel


router = APIRouter()


# ============================================================================
#  UNIWERSALNE NARZĘDZIA
# ============================================================================

def oid(value):
    """Zamienia string → ObjectId o ile jest valid."""
    try:
        return ObjectId(value)
    except:
        return value


def serialize_doc(doc: dict) -> dict:
    """Konwertuje wszystkie ObjectId w dokumencie na string."""
    out = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            out[key] = str(value)
        else:
            out[key] = value
    return out

async def enrich_loan(db, loan):
    """Uzupełnia wypożyczenie o dane książki i użytkownika."""
    
    loan = dict(loan)  # ← unikamy problemów z Cursor/Raw doc

    # Book
    try:
        book = await db.books.find_one({"_id": ObjectId(loan["book_id"])})
        if book:
            loan["book_title"] = book.get("title", "")
            loan["book_author"] = book.get("author", "")
            loan["book_image"] = book.get("image_url") or book.get("cover_image")
    except:
        pass

    # User
    try:
        user = await db.users.find_one({"_id": ObjectId(loan["user_id"])})
        if user:
            loan["username"] = user.get("username", "")
            loan["user_name"] = user.get("full_name", "")
    except:
        pass

    loan["is_overdue"] = (
        loan.get("status") == "active"
        and loan.get("due_date") is not None
        and datetime.utcnow() > loan["due_date"]
    )

    loan["_id"] = str(loan["_id"])

    return loan



# ============================================================================
#  LISTA WSZYSTKICH WYPOŻYCZEŃ (panel admina)
# ============================================================================

@router.get("/")
async def get_loans(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserInDB = Depends(get_current_active_user)
):
    if current_user.role not in ["admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Brak uprawnień")

    db = get_database()

    query = {"status": status} if status else {}

    cursor = db.loans.find(query).sort("loan_date", -1).skip((page - 1) * limit).limit(limit)

    loans = [enrich_loan(db, loan) async for loan in cursor]

    total = await db.loans.count_documents(query)

    return {
        "loans": loans,
        "total": total,
        "page": page,
        "limit": limit
    }


# ============================================================================
#  WYPOŻYCZENIA ZALOGOWANEGO UŻYTKOWNIKA
# ============================================================================

@router.get("/me")
async def get_my_loans(
    status: Optional[str] = Query(None),
    current_user: UserInDB = Depends(get_current_active_user)
):
    db = get_database()

    query = {"user_id": current_user.id}
    if status:
        query["status"] = status

    cursor = db.loans.find(query).sort("loan_date", -1)

    loans = []
    async for loan in cursor:
        loans.append(await enrich_loan(db, loan))  # ← KLUCZOWA POPRAWKA

    return loans



# ============================================================================
#  SZCZEGÓŁY WYPOŻYCZENIA
# ============================================================================

@router.get("/{loan_id}")
async def get_loan(
    loan_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    db = get_database()

    if not ObjectId.is_valid(loan_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID wypożyczenia")

    loan = await db.loans.find_one({"_id": oid(loan_id)})
    if not loan:
        raise HTTPException(status_code=404, detail="Wypożyczenie nie znalezione")

    if loan["user_id"] != current_user.id and current_user.role not in ["admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Brak uprawnień")

    return enrich_loan(db, loan)


# ============================================================================
#  UTWORZENIE WYPOŻYCZENIA
# ============================================================================

class LoanCreate(BaseModel):
    book_id: str
    librarian_notes: Optional[str] = None

@router.post("/", status_code=201)
async def create_loan(
    data: LoanCreate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    db = get_database()

    if not ObjectId.is_valid(data.book_id):
        raise HTTPException(status_code=400, detail="Nieprawidłowy ID książki")

    book = await db.books.find_one({"_id": oid(data.book_id)})
    if not book:
        raise HTTPException(404, "Książka nie znaleziona")

    if book.get("available_copies", 0) <= 0:
        raise HTTPException(400, "Brak dostępnych egzemplarzy")

    existing = await db.loans.find_one({
        "book_id": data.book_id,
        "user_id": current_user.id,
        "status": "active"
    })
    if existing:
        raise HTTPException(400, "Masz już wypożyczoną tę książkę")

    if await db.loans.count_documents({"user_id": current_user.id, "status": "active"}) >= 5:
        raise HTTPException(400, "Osiągnięto limit 5 wypożyczeń")

    loan = {
        "book_id": data.book_id,
        "user_id": current_user.id,
        "loan_date": datetime.utcnow(),
        "due_date": datetime.utcnow() + timedelta(days=30),
        "return_date": None,
        "status": "active",
        "renewal_count": 0,
        "max_renewals": 2,
        "librarian_notes": data.librarian_notes
    }

    result = await db.loans.insert_one(loan)

    await db.books.update_one(
        {"_id": oid(data.book_id)},
        {"$inc": {"available_copies": -1}}
    )

    created = await db.loans.find_one({"_id": result.inserted_id})

    return await enrich_loan(db, created)



# ============================================================================
#  ZWRÓĆ KSIĄŻKĘ
# ============================================================================

class LoanReturn(BaseModel):
    librarian_notes: Optional[str] = None


@router.post("/{loan_id}/return")
async def return_loan(
    loan_id: str,
    data: LoanReturn,
    current_user: UserInDB = Depends(get_current_active_user)
):
    db = get_database()

    loan = await db.loans.find_one({"_id": oid(loan_id)})
    if not loan:
        raise HTTPException(404, "Wypożyczenie nie znalezione")

    if loan["user_id"] != current_user.id and current_user.role not in ["admin", "librarian"]:
        raise HTTPException(403, "Brak uprawnień")

    if loan["status"] != "active":
        raise HTTPException(400, "To wypożyczenie nie jest aktywne")

    await db.loans.update_one(
        {"_id": oid(loan_id)},
        {
            "$set": {
                "status": "returned",
                "return_date": datetime.utcnow(),
                "librarian_notes": data.librarian_notes or loan.get("librarian_notes")
            }
        }
    )

    await db.books.update_one(
        {"_id": oid(loan["book_id"])},
        {"$inc": {"available_copies": 1}}
    )

    return {"message": "Książka została zwrócona"}


# ============================================================================
#  PRZEDŁUŻENIE WYPOŻYCZENIA
# ============================================================================

@router.post("/{loan_id}/renew")
async def renew_loan(loan_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    db = get_database()

    loan = await db.loans.find_one({"_id": oid(loan_id)})
    if not loan:
        raise HTTPException(404, "Wypożyczenie nie znalezione")

    if loan["user_id"] != current_user.id:
        raise HTTPException(403, "Brak uprawnień")

    if loan["status"] != "active":
        raise HTTPException(400, "Wypożyczenie nie jest aktywne")

    if loan["renewal_count"] >= loan["max_renewals"]:
        raise HTTPException(400, "Osiągnięto limit przedłużeń")

    new_due = loan["due_date"] + timedelta(days=14)

    await db.loans.update_one(
        {"_id": oid(loan_id)},
        {
            "$inc": {"renewal_count": 1},
            "$set": {"due_date": new_due}
        }
    )

    return {"message": "Przedłużono o 14 dni", "new_due_date": new_due.isoformat()}


# ============================================================================
#  SPRAWDŹ CZY MOŻNA WYPOŻYCZYĆ
# ============================================================================

@router.get("/can-borrow/{book_id}")
async def can_borrow(book_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    db = get_database()

    if not ObjectId.is_valid(book_id):
        return {"can_borrow": False, "reason": "Nieprawidłowy ID książki"}

    book = await db.books.find_one({"_id": oid(book_id)})
    if not book:
        return {"can_borrow": False, "reason": "Książka nie istnieje"}

    if book.get("available_copies", 0) <= 0:
        return {"can_borrow": False, "reason": "Brak dostępnych egzemplarzy"}

    if await db.loans.find_one({"book_id": book_id, "user_id": current_user.id, "status": "active"}):
        return {"can_borrow": False, "reason": "Masz już wypożyczoną tę książkę"}

    count = await db.loans.count_documents({"user_id": current_user.id, "status": "active"})
    if count >= 5:
        return {"can_borrow": False, "reason": "Limit 5 wypożyczeń"}

    return {"can_borrow": True}
