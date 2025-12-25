from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from bson import ObjectId

from ..models.dependencies import get_interaction_service
from ..service.interaction_service import InteractionService
from .auth import get_current_user
from ..database import get_database

router = APIRouter()


# ====== BODY MODELE (front wysyła JSON) ======
class BorrowBody(BaseModel):
    book_id: str


def to_object_id(id_str: str):
    """Konwertuje string ID na ObjectId jeśli to możliwe"""
    return ObjectId(id_str) if ObjectId.is_valid(id_str) else id_str


def pick_book_fields(book: dict):
    """Wyciąga najważniejsze pola z książki"""
    title = book.get("title") or book.get("book_title") or "Nieznany tytuł"
    author = book.get("author") or book.get("authors") or book.get("book_author") or ""
    image = book.get("image_url") or book.get("cover_url") or book.get("book_image") or None
    return title, author, image


@router.post("/borrow")
async def borrow_book(
    payload: BorrowBody,
    current_user=Depends(get_current_user),
    interaction_service: InteractionService = Depends(get_interaction_service),
):
    """
    Wypożycz książkę

    ✅ KOMPATYBILNOŚĆ: Tworzy zarówno loan_date (dla UI) jak i borrowed_at (dla recommendations)
    """
    db = get_database()
    user_id = current_user.id
    book_id = payload.book_id

    # 1. Sprawdź czy książka istnieje
    book_key = to_object_id(book_id)
    book = await db.books.find_one({"_id": book_key})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # 2. Sprawdź dostępność
    if book.get("available_copies", 0) <= 0:
        raise HTTPException(status_code=400, detail="No copies available")

    # 3. Sprawdź limit wypożyczeń (bez book_id w query!)
    active_loans = await db.loans.count_documents({"user_id": user_id, "status": "active"})
    if active_loans >= 10:
        raise HTTPException(status_code=400, detail="Loan limit reached (max 10)")

    # 4. Sprawdź czy użytkownik już nie ma wypożyczonej tej książki
    existing = await db.loans.find_one({"user_id": user_id, "book_id": book_id, "status": "active"})
    if existing:
        raise HTTPException(status_code=400, detail="You already borrowed this book")

    # 5. Przygotuj dane książki
    book_title, book_author, book_image = pick_book_fields(book)

    # 6. Utwórz wypożyczenie
    now = datetime.utcnow()
    loan_doc = {
        "user_id": user_id,
        "book_id": book_id,
        "book_title": book_title,
        "book_author": book_author,
        "book_image": book_image,
        # ✅ KOMPATYBILNOŚĆ: Oba pola dla różnych części systemu
        "loan_date": now,  # Używane przez UI (MyLoans.jsx)
        "borrowed_at": now,  # Używane przez recommendations (because-borrowed endpoint)
        "due_date": now + timedelta(days=30),
        "return_date": None,
        "status": "active",
        "renewal_count": 0,
        "max_renewals": 2,
        "created_at": now,
    }

    result = await db.loans.insert_one(loan_doc)
    loan_id = str(result.inserted_id)

    # 7. Zmniejsz available_copies
    await db.books.update_one({"_id": book_key}, {"$inc": {"available_copies": -1}})

    # 8. Utwórz interakcję (waga 1.0 dla borrow)
    interaction_result = await interaction_service.create_interaction(
        user_id=user_id,
        book_id=book_id,
        interaction_type="borrow",
        metadata={"loan_id": loan_id, "loan_date": loan_doc["loan_date"].isoformat()},
        update_embedding=True,
    )

    # 9. Zwróć wynik
    loan_doc["_id"] = loan_id
    return {
        **loan_doc,
        "interaction_created": True,
        "interaction_weight": 1.0,
        "embedding_updated": interaction_result.get("embedding_updated", False),
    }


@router.get("/my-loans")
async def get_my_loans(current_user=Depends(get_current_user), status: str | None = None):
    """
    Pobierz wypożyczenia użytkownika

    ✅ KOMPATYBILNOŚĆ: Sortuje po loan_date (główne pole)
    """
    db = get_database()
    user_id = current_user.id

    query = {"user_id": user_id}
    if status:
        query["status"] = status

    loans = await db.loans.find(query).sort("loan_date", -1).to_list(length=200)

    # Uzupełnij brakujące pola dla starszych rekordów
    for loan in loans:
        loan["_id"] = str(loan["_id"])

        # ✅ KOMPATYBILNOŚĆ: Dodaj borrowed_at jeśli brakuje
        if "borrowed_at" not in loan and "loan_date" in loan:
            loan["borrowed_at"] = loan["loan_date"]

        # ✅ KOMPATYBILNOŚĆ: Dodaj loan_date jeśli brakuje (stare rekordy)
        if "loan_date" not in loan and "borrowed_at" in loan:
            loan["loan_date"] = loan["borrowed_at"]

        # Legacy: borrow_date → loan_date
        if "loan_date" not in loan and "borrow_date" in loan:
            loan["loan_date"] = loan["borrow_date"]
            loan["borrowed_at"] = loan["borrow_date"]

        # Uzupełnij dane książki jeśli brakują
        if not loan.get("book_title") or not loan.get("book_author") or not loan.get("book_image"):
            book_key = to_object_id(str(loan.get("book_id")))
            book = await db.books.find_one({"_id": book_key})
            if book:
                title, author, image = pick_book_fields(book)
                loan["book_title"] = loan.get("book_title") or title
                loan["book_author"] = loan.get("book_author") or author
                loan["book_image"] = loan.get("book_image") or image

    return loans


@router.get("/me")
async def get_my_loans_alias(current_user=Depends(get_current_user), status: str | None = None):
    """
    Alias dla /my-loans
    Używany przez frontend: loansAPI.getMine()
    """
    return await get_my_loans(current_user=current_user, status=status)


@router.post("/{loan_id}/return")
async def return_book(loan_id: str, current_user=Depends(get_current_user)):
    """Zwróć wypożyczoną książkę"""
    db = get_database()
    user_id = current_user.id

    loan_key = to_object_id(loan_id)
    loan = await db.loans.find_one({"_id": loan_key})
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if loan["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not your loan")

    if loan["status"] != "active":
        raise HTTPException(status_code=400, detail="Already returned")

    # Zaktualizuj status
    await db.loans.update_one(
        {"_id": loan_key},
        {"$set": {"status": "returned", "return_date": datetime.utcnow()}},
    )

    # Zwiększ available_copies
    book_key = to_object_id(str(loan["book_id"]))
    await db.books.update_one({"_id": book_key}, {"$inc": {"available_copies": 1}})

    return {"message": "Book returned successfully"}


@router.post("/{loan_id}/renew")
async def renew_loan(loan_id: str, current_user=Depends(get_current_user)):
    """Przedłuż wypożyczenie"""
    db = get_database()
    user_id = current_user.id

    loan_key = to_object_id(loan_id)
    loan = await db.loans.find_one({"_id": loan_key})
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if loan["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not your loan")

    if loan["status"] != "active":
        raise HTTPException(status_code=400, detail="Cannot renew returned loan")

    # Sprawdź limit przedłużeń
    renewal_count = loan.get("renewal_count", 0)
    max_renewals = loan.get("max_renewals", 2)
    if renewal_count >= max_renewals:
        raise HTTPException(status_code=400, detail="Renewal limit reached")

    # Przedłuż o 14 dni
    new_due = loan["due_date"] + timedelta(days=14)

    await db.loans.update_one(
        {"_id": loan_key},
        {"$set": {"due_date": new_due}, "$inc": {"renewal_count": 1}},
    )

    return {"message": "Loan renewed", "new_due_date": new_due}
