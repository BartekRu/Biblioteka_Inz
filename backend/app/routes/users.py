from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from bson import ObjectId
from pydantic import BaseModel

from ..database import get_database
from ..models.user import UserInDB, UserResponse, UserUpdate
from ..routes.auth import get_current_active_user

try:
    from recommendation_engine.service import get_recommendations_for_goodbooks_user
    LIGHTGCN_AVAILABLE = True
except ImportError:
    LIGHTGCN_AVAILABLE = False
    print("⚠️ LightGCN service not available - using fallback recommendations")

router = APIRouter()


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



class RecommendedBook(BaseModel):
    book_id: str
    title: str
    author: str
    genre: Optional[List[str]] = None
    average_rating: Optional[float] = None
    score: float
    recommendation_type: str = "popular" 
    match_reason: Optional[str] = None  



@router.get("/me/recommendations", response_model=List[RecommendedBook])
async def get_my_recommendations(
    n: int = Query(default=10, ge=1, le=50),
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Pobierz spersonalizowane rekomendacje książek.
    
    Priorytet:
    1. Użytkownik ma goodbooks_user_id → LightGCN collaborative filtering
    2. Użytkownik ma preferencje (gatunki/autorzy) → Content-based filtering
    3. Fallback → Popularne książki
    """
    db = get_database()
    
    user_doc = await db.users.find_one({"_id": ObjectId(current_user.id)})
    
    favorite_genres = user_doc.get("favorite_genres", []) or []
    favorite_authors = user_doc.get("favorite_authors", []) or []
    goodbooks_user_id = user_doc.get("goodbooks_user_id")

    if LIGHTGCN_AVAILABLE and goodbooks_user_id:
        try:
            recs = get_recommendations_for_goodbooks_user(
                user_goodbooks_id=goodbooks_user_id,
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
                        genre=book.get("genre", []),
                        average_rating=book.get("average_rating"),
                        score=float(rec["score"]),
                        recommendation_type="collaborative",
                        match_reason="Rekomendacja AI na podstawie Twojej historii"
                    )
                )

            if recommended_books:
                return recommended_books
                
        except Exception as e:
            print(f"LightGCN recommendation failed: {e}")

    if favorite_genres or favorite_authors:
        return await get_content_based_recommendations(
            db, n, favorite_genres, favorite_authors, current_user
        )

    return await get_popular_books_fallback(db, n, current_user)


async def get_content_based_recommendations(
    db,
    n: int,
    favorite_genres: List[str],
    favorite_authors: List[str],
    current_user: UserInDB
) -> List[RecommendedBook]:
    """
    Rekomendacje content-based na podstawie ulubionych gatunków i autorów.
    
    Scoring:
    - +3 punkty za matching autora
    - +2 punkty za każdy matching gatunek
    - +1 punkt za wysoką ocenę (>4.0)
    """
    
    or_conditions = []
    
    if favorite_genres:
        genre_regex = [{"genre": {"$regex": g, "$options": "i"}} for g in favorite_genres]
        or_conditions.extend(genre_regex)
    
    if favorite_authors:
        author_regex = [{"author": {"$regex": a, "$options": "i"}} for a in favorite_authors]
        or_conditions.extend(author_regex)
    
    if not or_conditions:
        return await get_popular_books_fallback(db, n, current_user)
    
    cursor = db.books.find({"$or": or_conditions}).limit(n * 3)
    candidates = await cursor.to_list(length=n * 3)
    
    scored_books = []
    for book in candidates:
        score = 0.0
        match_reasons = []
        
        book_author = book.get("author", "").lower()
        book_genres = [g.lower() for g in book.get("genre", [])]
        
        for fav_author in favorite_authors:
            if fav_author.lower() in book_author:
                score += 3.0
                match_reasons.append(f"Autor: {book.get('author')}")
                break
        
        matched_genres = []
        for fav_genre in favorite_genres:
            for book_genre in book_genres:
                if fav_genre.lower() in book_genre:
                    score += 2.0
                    matched_genres.append(fav_genre)
                    break
        
        if matched_genres:
            match_reasons.append(f"Gatunki: {', '.join(matched_genres)}")
        
        avg_rating = book.get("average_rating", 0)
        if avg_rating and avg_rating > 4.0:
            score += 1.0
        
        if score > 0:
            scored_books.append({
                "book": book,
                "score": score,
                "match_reason": " | ".join(match_reasons) if match_reasons else None
            })
    
    scored_books.sort(key=lambda x: x["score"], reverse=True)
    
    recommendations = []
    for item in scored_books[:n]:
        book = item["book"]
        recommendations.append(
            RecommendedBook(
                book_id=str(book["_id"]),
                title=book["title"],
                author=book.get("author", ""),
                genre=book.get("genre", []),
                average_rating=book.get("average_rating"),
                score=item["score"],
                recommendation_type="content_based",
                match_reason=item["match_reason"]
            )
        )
    
    if len(recommendations) < n:
        popular = await get_popular_books_fallback(
            db, 
            n - len(recommendations), 
            current_user,
            exclude_ids=[r.book_id for r in recommendations]
        )
        recommendations.extend(popular)
    
    return recommendations


async def get_popular_books_fallback(
    db, 
    n: int, 
    current_user: UserInDB,
    exclude_ids: List[str] = None
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
                match_reason="Popularna książka"
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
    
    await db.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": update_data}
    )
    
    doc = await db.users.find_one({"_id": ObjectId(current_user.id)})
    doc["_id"] = str(doc["_id"])
    return UserResponse(**doc)