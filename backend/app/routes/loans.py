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
    # pozwala działać i dla stringowych _id, i dla ObjectId
    return ObjectId(id_str) if ObjectId.is_valid(id_str) else id_str


def pick_book_fields(book: dict):
    # dopasuj do swoich pól w books
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
    db = get_database()
    user_id = current_user.id
    book_id = payload.book_id

    # książka
    book_key = to_object_id(book_id)
    book = await db.books.find_one({"_id": book_key})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.get("available_copies", 0) <= 0:
        raise HTTPException(status_code=400, detail="No copies available")

    # limit aktywnych wypożyczeń (UWAGA: bez book_id w query!)
    active_loans = await db.loans.count_documents({"user_id": user_id, "status": "active"})
    if active_loans >= 10:
        raise HTTPException(status_code=400, detail="Loan limit reached (max 5)")

    # duplikat: aktywne wypożyczenie tej samej książki
    existing = await db.loans.find_one({"user_id": user_id, "book_id": book_id, "status": "active"})
    if existing:
        raise HTTPException(status_code=400, detail="You already borrowed this book")

    book_title, book_author, book_image = pick_book_fields(book)

    now = datetime.utcnow()
    loan_doc = {
        "user_id": user_id,
        "book_id": book_id,  # trzymamy jako string pod frontend
        "book_title": book_title,
        "book_author": book_author,
        "book_image": book_image,
        "loan_date": now,  # UI używa loan_date
        "due_date": now + timedelta(days=30),  # u Ciebie na screenie było ~30 dni
        "return_date": None,
        "status": "active",  # UI używa 'active'
        "renewal_count": 0,
        "max_renewals": 2,
        "created_at": now,
    }

    result = await db.loans.insert_one(loan_doc)
    loan_id = str(result.inserted_id)

    await db.books.update_one({"_id": book_key}, {"$inc": {"available_copies": -1}})

    # interakcja borrow (waga 1.0)
    interaction_result = await interaction_service.create_interaction(
        user_id=user_id,
        book_id=book_id,
        interaction_type="borrow",
        metadata={"loan_id": loan_id, "loan_date": loan_doc["loan_date"].isoformat()},
        update_embedding=True,
    )

    loan_doc["_id"] = loan_id
    return {
        **loan_doc,
        "interaction_created": True,
        "interaction_weight": 1.0,
        "embedding_updated": interaction_result.get("embedding_updated", False),
    }


@router.get("/my-loans")
async def get_my_loans(current_user=Depends(get_current_user), status: str | None = None):
    db = get_database()
    user_id = current_user.id

    query = {"user_id": user_id}
    if status:
        query["status"] = status

    loans = await db.loans.find(query).sort("loan_date", -1).to_list(length=200)

    # uzupełnij brakujące pola (stare rekordy) żeby nie było "Nieznany tytuł"
    for loan in loans:
        loan["_id"] = str(loan["_id"])
        # kompatybilność jeśli gdzieś masz borrow_date zamiast loan_date
        if "loan_date" not in loan and "borrow_date" in loan:
            loan["loan_date"] = loan["borrow_date"]

        if not loan.get("book_title") or not loan.get("book_author") or not loan.get("book_image"):
            book_key = to_object_id(str(loan.get("book_id")))
            book = await db.books.find_one({"_id": book_key})
            if book:
                title, author, image = pick_book_fields(book)
                loan["book_title"] = loan.get("book_title") or title
                loan["book_author"] = loan.get("book_author") or author
                loan["book_image"] = loan.get("book_image") or image

    return loans


# alias pod frontend: loansAPI.getMine() -> /loans/me
@router.get("/me")
async def get_my_loans_alias(current_user=Depends(get_current_user), status: str | None = None):
    return await get_my_loans(current_user=current_user, status=status)


@router.post("/{loan_id}/return")
async def return_book(loan_id: str, current_user=Depends(get_current_user)):
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

    await db.loans.update_one(
        {"_id": loan_key},
        {"$set": {"status": "returned", "return_date": datetime.utcnow()}},
    )

    book_key = to_object_id(str(loan["book_id"]))
    await db.books.update_one({"_id": book_key}, {"$inc": {"available_copies": 1}})

    return {"message": "Book returned successfully"}


@router.post("/{loan_id}/renew")
async def renew_loan(loan_id: str, current_user=Depends(get_current_user)):
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

    renewal_count = loan.get("renewal_count", 0)
    max_renewals = loan.get("max_renewals", 2)
    if renewal_count >= max_renewals:
        raise HTTPException(status_code=400, detail="Renewal limit reached")

    new_due = loan["due_date"] + timedelta(days=14)

    await db.loans.update_one(
        {"_id": loan_key},
        {"$set": {"due_date": new_due}, "$inc": {"renewal_count": 1}},
    )

    return {"message": "Loan renewed", "new_due_date": new_due}
