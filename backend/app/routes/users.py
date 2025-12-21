from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from bson import ObjectId
from pydantic import BaseModel
from collections import Counter
from datetime import datetime, timedelta

from app.routes.recommendations import normalize_book, serialize_doc
import logging  # ← DODANE
from collections import Counter

logger = logging.getLogger(__name__)

from ..database import get_database
from ..models.user import UserInDB, UserResponse, UserUpdate
from ..routes.auth import get_current_active_user, get_current_user

try:
    from recommendation_engine.service import get_recommendations_for_goodbooks_user

    LIGHTGCN_AVAILABLE = True
except ImportError:
    LIGHTGCN_AVAILABLE = False
    print("⚠️ LightGCN service not available - using fallback recommendations")

router = APIRouter()


def normalize_object_id(value):
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str):
        try:
            return ObjectId(value)
        except Exception:
            return None
    return None


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: UserInDB = Depends(get_current_active_user),
) -> UserResponse:
    user_dict = current_user.model_dump()
    user_dict["_id"] = str(user_dict.pop("id"))
    return UserResponse(**user_dict)


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    user_update: UserUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
) -> UserResponse:
    db = get_database()

    update_data = {
        k: v for k, v in user_update.model_dump(exclude_unset=True).items() if v is not None
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


class RecommendedBook(BaseModel):
    book_id: str
    title: str
    author: str
    genre: Optional[List[str]] = None
    average_rating: Optional[float] = None
    score: float
    recommendation_type: str = "popular"
    match_reason: Optional[str] = None


@router.get("/me/recommendations")
async def get_user_recommendations(
    n: int = Query(default=10, le=30),
    offset: int = Query(default=0, ge=0),  # ← DODANE - dla rotacji
    randomize: bool = Query(default=False),  # ← DODANE - opcjonalna randomizacja
    current_user=Depends(get_current_user),
):
    """
    Rekomendacje oparte na favorite_genres i favorite_authors.

    Parametry:
    - n: ile książek zwrócić
    - offset: pomiń pierwsze X książek (dla rotacji)
    - randomize: czy losowo wymieszać wyniki
    """
    db = get_database()
    user_id = ObjectId(str(current_user.id))

    favorite_genres = current_user.favorite_genres or []
    favorite_authors = current_user.favorite_authors or []

    if not favorite_genres and not favorite_authors:
        raise HTTPException(
            status_code=400,
            detail="Dodaj ulubione gatunki lub autorów, aby otrzymać rekomendacje.",
        )

    # 🔍 Pobierz WIĘCEJ książek niż potrzeba (dla rotacji)
    fetch_limit = n + offset + 50  # Buffer na rotację

    # Pipeline aggregacji
    pipeline = []
    match_conditions = []

    if favorite_genres:
        match_conditions.append({"genre": {"$in": favorite_genres}})
    if favorite_authors:
        match_conditions.append({"authors": {"$in": favorite_authors}})

    if match_conditions:
        pipeline.append({"$match": {"$or": match_conditions}})

    # Wyklucz wypożyczone książki
    borrowed = await db.loans.find({"user_id": user_id, "status": "active"}).distinct("book_id")

    if borrowed:
        pipeline.append({"$match": {"_id": {"$nin": borrowed}}})

    # Oblicz score
    pipeline.append(
        {
            "$addFields": {
                "genre_match_count": {
                    "$size": {
                        "$setIntersection": [
                            {"$ifNull": ["$genre", []]},
                            favorite_genres,
                        ]
                    }
                },
                "author_match_count": {
                    "$size": {
                        "$setIntersection": [
                            {"$ifNull": ["$authors", []]},
                            favorite_authors,
                        ]
                    }
                },
            }
        }
    )

    pipeline.append(
        {
            "$addFields": {
                "score": {
                    "$add": [
                        {"$multiply": ["$genre_match_count", 2.0]},
                        {"$multiply": ["$author_match_count", 3.0]},
                        {"$multiply": [{"$ifNull": ["$average_rating", 0]}, 0.5]},
                    ]
                }
            }
        }
    )

    # ✅ RANDOMIZACJA (opcjonalna)
    if randomize:
        pipeline.append({"$sample": {"size": fetch_limit}})
    else:
        pipeline.append({"$sort": {"score": -1}})
        pipeline.append({"$limit": fetch_limit})

    books_cursor = db.books.aggregate(pipeline)
    all_books = await books_cursor.to_list(length=fetch_limit)

    # ✅ ZASTOSUJ OFFSET (pomiń pierwsze X)
    books_after_offset = all_books[offset : offset + n]

    recommendations = []
    for book in books_after_offset:
        rec_type = "content_based"
        match_reason = None

        genre_matches = book.get("genre_match_count", 0)
        author_matches = book.get("author_match_count", 0)

        if genre_matches > 0 and author_matches > 0:
            match_reason = f"Gatunek i autor: {', '.join(book.get('genre', [])[:1])}, {', '.join(book.get('authors', [])[:1])}"
        elif genre_matches > 0:
            match_reason = f"Gatunek: {', '.join(book.get('genre', [])[:2])}"
        elif author_matches > 0:
            match_reason = f"Autor: {', '.join(book.get('authors', [])[:1])}"

        book_data = normalize_book(serialize_doc(book))
        recommendations.append(
            {
                **book_data,
                "recommendation_type": rec_type,
                "score": book.get("score", 0),
                "match_reason": match_reason,
            }
        )

    logger.info(
        f"✅ Returning {len(recommendations)} recommendations for user {user_id} "
        f"(offset={offset}, randomize={randomize})"
    )

    return recommendations


async def get_popular_books_fallback(
    db, n: int, current_user: UserInDB, exclude_ids: List[str] = None
) -> List[RecommendedBook]:
    """
    Fallback: popularne książki posortowane po average_rating.
    """
    exclude_ids = exclude_ids or []

    query = {}
    if exclude_ids:
        query["_id"] = {"$nin": [ObjectId(id) for id in exclude_ids]}

    cursor = db.books.find(query).sort("average_rating", -1).limit(n)
    books = await cursor.to_list(length=n)

    recommendations = []
    for book in books:
        recommendations.append(
            RecommendedBook(
                book_id=str(book["_id"]),
                title=book["title"],
                author=book.get("author", ""),
                genre=book.get("genre", []),
                average_rating=book.get("average_rating"),
                score=book.get("average_rating", 0) or 0,
                recommendation_type="popular",
                match_reason="Popularna książka",
            )
        )

    return recommendations


class UserPreferencesInput(BaseModel):
    favorite_genres: Optional[List[str]] = None
    favorite_authors: Optional[List[str]] = None


@router.post("/me/preferences", response_model=UserResponse)
async def set_my_preferences(
    preferences: UserPreferencesInput,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Zapisz preferencje użytkownika i zwróć zaktualizowany profil.
    """
    db = get_database()

    update_data = {"updated_at": datetime.utcnow()}

    if preferences.favorite_genres is not None:
        update_data["favorite_genres"] = preferences.favorite_genres
    if preferences.favorite_authors is not None:
        update_data["favorite_authors"] = preferences.favorite_authors

    await db.users.update_one({"_id": ObjectId(current_user.id)}, {"$set": update_data})

    doc = await db.users.find_one({"_id": ObjectId(current_user.id)})
    doc["_id"] = str(doc["_id"])
    return UserResponse(**doc)


@router.get("/me/stats")
async def get_user_stats(current_user=Depends(get_current_user)):
    """
    📊 Statystyki użytkownika oparte na FAKTYCZNYCH interakcjach
    - Top 3 gatunki (z wypożyczeń i recenzji)
    - Top 3 autorzy
    - Liczba interakcji
    - Średnia ocen
    """
    db = get_database()

    user_id_oid = ObjectId(str(current_user.id))
    user_id_str = str(current_user.id)

    genre_counter = Counter()
    author_counter = Counter()
    total_borrows = 0
    total_reviews = 0
    total_views = 0
    ratings_sum = 0
    ratings_count = 0

    async for loan in db.loans.find({"user_id": user_id_oid}):
        total_borrows += 1
        book_id = normalize_object_id(review.get("book_id"))

        book = await db.books.find_one({"_id": book_id}) if book_id else None

        if book:
            genres = book.get("genre", [])
            if isinstance(genres, str):
                genres = [genres]
            for genre in genres:
                if genre:
                    genre_counter[genre] += 2

            authors = book.get("authors") or book.get("author") or []
            if isinstance(authors, str):
                authors = [authors]
            for author in authors:
                if author:
                    author_counter[author] += 2

    # Jeśli total_borrows == 0, spróbuj ze stringiem
    if total_borrows == 0:
        logger.warning(f"⚠️ No loans found with ObjectId, trying string...")
        async for loan in db.loans.find({"user_id": user_id_str}):
            total_borrows += 1
            book_id = normalize_object_id(loan.get("book_id"))
            book = await db.books.find_one({"_id": book_id}) if book_id else None

            if book:
                genres = book.get("genre", [])
                if isinstance(genres, str):
                    genres = [genres]
                for genre in genres:
                    if genre:
                        genre_counter[genre] += 2

                authors = book.get("authors") or book.get("author") or []
                if isinstance(authors, str):
                    authors = [authors]
                for author in authors:
                    if author:
                        author_counter[author] += 2

    # ✅ Recenzje - SZUKAJ PO OBYDWU
    async for review in db.reviews.find(
        {"$or": [{"user_id": user_id_oid}, {"user_id": user_id_str}]}
    ):
        total_reviews += 1
        rating = review.get("rating")
        if rating:
            ratings_sum += rating
            ratings_count += 1

        book_id = normalize_object_id(loan.get("book_id"))
        book = await db.books.find_one({"_id": book_id}) if book_id else None

        if book:
            genres = book.get("genre", [])
            if isinstance(genres, str):
                genres = [genres]
            for genre in genres:
                if genre:
                    genre_counter[genre] += 1

            authors = book.get("authors") or book.get("author") or []
            if isinstance(authors, str):
                authors = [authors]
            for author in authors:
                if author:
                    author_counter[author] += 1

    # ✅ Views - SZUKAJ PO STRINGU (interactions używa stringów)
    total_views = await db.interactions.count_documents(
        {"user_id": user_id_str, "interaction_type": "view"}
    )

    # 2. Top 3 gatunki i autorzy
    top_genres = [{"genre": genre, "count": count} for genre, count in genre_counter.most_common(3)]

    top_authors = [
        {"author": author, "count": count} for author, count in author_counter.most_common(3)
    ]

    # 3. Średnia ocen
    avg_rating = round(ratings_sum / ratings_count, 2) if ratings_count > 0 else None

    logger.info(
        f"📊 Stats for user {user_id_str[:8]}: "
        f"borrows={total_borrows}, reviews={total_reviews}, views={total_views}"
    )

    return {
        "total_interactions": total_borrows + total_reviews + total_views,
        "total_borrows": total_borrows,
        "total_reviews": total_reviews,
        "total_views": total_views,
        "avg_rating": avg_rating,
        "top_genres": top_genres,
        "top_authors": top_authors,
        "declared_genres": current_user.favorite_genres or [],
        "declared_authors": current_user.favorite_authors or [],
    }
