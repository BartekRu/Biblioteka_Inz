"""
Discovery Endpoints Module
===========================

Advanced discovery endpoints extracted from recommendations.py
All /by-genre, /by-author, /similar-readers, /new-arrivals, /hidden-gems, /highly-rated
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional
from datetime import datetime, timedelta
from collections import Counter
from bson import ObjectId
import numpy as np
import logging

from .recommendation_helpers import (
    normalize_book,
    serialize_doc,
    enrich_recommendations_with_metadata,
    calculate_content_similarity,
)
from .user_analysis import get_user_top_genres, get_user_favorite_authors
from ..database import get_database
from .auth import get_current_user

# MMR imports
try:
    from recommendation_engine.mmr_reranking import mmr_rerank, diversity_metrics

    MMR_AVAILABLE = True
except ImportError:
    MMR_AVAILABLE = False

logger = logging.getLogger(__name__)
router = APIRouter()


def get_service():
    """Lazy load LightGCN service"""
    import recommendation_engine.goodbooks_lightgcn_service as service_module

    if service_module.goodbooks_lgcn_service is None:
        raise HTTPException(503, detail="Service not initialized")
    return service_module.goodbooks_lgcn_service


def _to_numpy_vector(vector) -> Optional[np.ndarray]:
    if vector is None:
        return None
    if hasattr(vector, "detach"):
        vector = vector.detach().cpu().numpy()
    return np.asarray(vector, dtype=float)


def _safe_cosine(vec_a, vec_b) -> Optional[float]:
    a = _to_numpy_vector(vec_a)
    b = _to_numpy_vector(vec_b)
    if a is None or b is None:
        return None
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return None
    return float(np.dot(a, b) / (norm_a * norm_b))


def _to_book_query_id(book_id):
    if isinstance(book_id, ObjectId):
        return book_id
    if isinstance(book_id, str) and ObjectId.is_valid(book_id):
        return ObjectId(book_id)
    return book_id


async def _get_user_read_book_ids(db, user_id: str) -> set:
    interactions = await db.interactions.find(
        {"user_id": user_id, "interaction_type": {"$in": ["borrow", "review"]}}
    ).to_list(length=None)
    book_ids = {item["book_id"] for item in interactions if item.get("book_id")}

    loans = await db.loans.find({"user_id": user_id}).to_list(length=None)
    book_ids.update(item["book_id"] for item in loans if item.get("book_id"))

    return book_ids


async def _hydrate_ranked_books(
    db,
    ranked_books,
    limit: int,
    lightgcn=None,
    user_embedding=None,
):
    ranked_books = ranked_books[:limit]
    if not ranked_books:
        return []

    book_ids = [book_id for book_id, _ in ranked_books]
    books = await db.books.find(
        {"_id": {"$in": [_to_book_query_id(book_id) for book_id in book_ids]}}
    ).to_list(length=None)
    book_dict = {str(book["_id"]): normalize_book(serialize_doc(book)) for book in books}
    max_count = ranked_books[0][1] if ranked_books else 1

    result_books = []
    for book_id, count in ranked_books:
        book = book_dict.get(str(book_id))
        if not book:
            continue

        book["popularityScore"] = count / max_count if max_count else 0
        book["popularityCount"] = count

        if lightgcn is not None and user_embedding is not None:
            try:
                gb_id = book.get("goodbooks_book_id")
                book_idx = lightgcn.book_id_to_item_idx.get(int(gb_id)) if gb_id else None
                if book_idx is not None:
                    score = _safe_cosine(user_embedding, lightgcn.item_emb[book_idx])
                    if score is not None:
                        book["matchScore"] = score
            except Exception:
                pass

        result_books.append(book)

    return result_books


async def _similar_readers_fallback(db, user_id: str, limit: int, reason: str):
    user_book_ids = await _get_user_read_book_ids(db, user_id)
    user_book_id_list = list(user_book_ids)

    source = "popular_cold_start"
    similar_user_count = 0
    ranked_books = []

    if user_book_id_list:
        overlap_rows = await db.interactions.find(
            {
                "user_id": {"$ne": user_id},
                "book_id": {"$in": user_book_id_list},
                "interaction_type": {"$in": ["borrow", "review"]},
            }
        ).to_list(length=None)

        similar_counts = Counter(row["user_id"] for row in overlap_rows if row.get("user_id"))
        similar_user_ids = [user for user, _ in similar_counts.most_common(50)]
        similar_user_count = len(similar_user_ids)

        if similar_user_ids:
            similar_interactions = await db.interactions.find(
                {
                    "user_id": {"$in": similar_user_ids},
                    "interaction_type": {"$in": ["borrow", "review"]},
                }
            ).to_list(length=None)
            popularity = Counter()
            for interaction in similar_interactions:
                book_id = interaction.get("book_id")
                if book_id and book_id not in user_book_ids:
                    popularity[book_id] += similar_counts.get(interaction.get("user_id"), 1)

            ranked_books = popularity.most_common(limit)
            if ranked_books:
                source = "interaction_overlap"

    if not ranked_books:
        popular_rows = await db.interactions.aggregate(
            [
                {"$match": {"interaction_type": {"$in": ["borrow", "review"]}}},
                {"$group": {"_id": "$book_id", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": limit * 3},
            ]
        ).to_list(length=None)
        ranked_books = [
            (row["_id"], row["count"])
            for row in popular_rows
            if row.get("_id") and row["_id"] not in user_book_ids
        ][:limit]

    books = await _hydrate_ranked_books(db, ranked_books, limit)

    return {
        "books": books,
        "similar_user_count": similar_user_count,
        "metadata": {
            "fallback_used": True,
            "source": source,
            "reason": reason,
            "similar_users_found": similar_user_count,
            "user_history_count": len(user_book_ids),
        },
    }


@router.get("/by-genre")
async def get_genre_recommendations(
    limit: int = Query(3, ge=1, le=5, description="Liczba gatunków"),
    books_per_genre: int = Query(10, ge=5, le=20, description="Książek na gatunek"),
    current_user=Depends(get_current_user),
):
    """SEKCJA B: Rekomendacje według gatunku"""
    db = get_database()
    user_id = str(current_user.id)

    # Znajdź top gatunki
    top_genres = await get_user_top_genres(db, user_id, limit)

    print(f"🔍 DEBUG - top_genres: {top_genres}")

    if not top_genres:
        print("❌ DEBUG - No top genres found!")
        return []

    # Pobierz embedding użytkownika
    lightgcn = None
    user_embedding = None

    try:
        lightgcn = get_service()
        user_idx = lightgcn.mongo_user_to_idx.get(user_id)
        user_embedding = lightgcn.user_emb[user_idx] if user_idx is not None else None
    except:
        user_embedding = None

    sections = []
    for genre_info in top_genres:
        genre = genre_info["genre"]

        print(f"🔍 DEBUG - Searching for genre: {genre}")

        # Obsługa zarówno genre: "Fantasy" jak i genre: ["Fantasy", "Young Adult"]
        genre_books = await db.books.find(
            {
                "$or": [
                    {"genre": genre},  # genre jako string
                    {"genres": genre},  # fallback dla genres
                ],
                "available_copies": {"$gt": 0},
            }
        ).to_list(length=100)

        print(f"📚 DEBUG - Found {len(genre_books)} books for genre {genre}")

        if not genre_books:
            continue

        # Personalizuj ranking
        scored_books = []
        for book in genre_books:
            book_data = normalize_book(serialize_doc(book))

            # Spróbuj użyć LightGCN
            if user_embedding is not None:
                try:
                    gb_id = book.get("goodbooks_book_id")
                    book_idx = lightgcn.book_id_to_item_idx.get(int(gb_id)) if gb_id else None

                    if book_idx is not None:
                        book_embedding = lightgcn.item_emb[book_idx]
                        score = np.dot(user_embedding, book_embedding) / (
                            np.linalg.norm(user_embedding) * np.linalg.norm(book_embedding)
                        )
                        book_data["matchScore"] = float(score)
                    else:
                        book_data["matchScore"] = 0.5
                except:
                    book_data["matchScore"] = 0.5
            else:
                book_data["matchScore"] = 0.5

            scored_books.append(book_data)

        # Sortuj i zwróć top N
        scored_books.sort(key=lambda x: x.get("matchScore", 0), reverse=True)

        sections.append(
            {
                "genre": genre,
                "books": scored_books[:books_per_genre],
                "user_preference_score": genre_info["score"],
            }
        )

    return sections


@router.get("/by-author")
async def get_author_recommendations(
    limit: int = Query(3, ge=1, le=5),
    books_per_author: int = Query(10, ge=5, le=20),
    current_user=Depends(get_current_user),
):
    """SEKCJA B: Rekomendacje według autora"""
    db = get_database()
    user_id = str(current_user.id)

    # Znajdź ulubionych autorów
    favorite_authors = await get_user_favorite_authors(db, user_id, limit)

    if not favorite_authors:
        return []

    # Pobierz embedding użytkownika
    try:
        lightgcn = get_service()
        user_idx = lightgcn.mongo_user_to_idx.get(user_id)
        user_embedding = lightgcn.user_emb[user_idx] if user_idx is not None else None
    except:
        user_embedding = None

    # Pobierz już wypożyczone książki
    user_borrows = await db.interactions.find(
        {"user_id": user_id, "interaction_type": "borrow"}
    ).to_list(length=None)
    borrowed_book_ids = [
        (
            ObjectId(i["book_id"])
            if isinstance(i.get("book_id"), str) and ObjectId.is_valid(i["book_id"])
            else i.get("book_id")
        )
        for i in user_borrows
        if i.get("book_id")
    ]

    sections = []
    for author_info in favorite_authors:
        author = author_info["author"]

        # Pobierz książki autora
        author_books = await db.books.find(
            {
                "author": author,
                "_id": {"$nin": list(borrowed_book_ids)},
                "available_copies": {"$gt": 0},
            }
        ).to_list(length=50)

        if not author_books:
            continue

        # Personalizuj
        scored_books = []
        for book in author_books:
            book_data = normalize_book(serialize_doc(book))

            if user_embedding is not None:
                try:
                    gb_id = book.get("goodbooks_book_id")
                    book_idx = lightgcn.book_id_to_item_idx.get(int(gb_id)) if gb_id else None

                    if book_idx is not None:
                        book_embedding = lightgcn.item_emb[book_idx]
                        score = np.dot(user_embedding, book_embedding) / (
                            np.linalg.norm(user_embedding) * np.linalg.norm(book_embedding)
                        )
                        book_data["matchScore"] = float(score)
                    else:
                        book_data["matchScore"] = 0.5
                except:
                    book_data["matchScore"] = 0.5
            else:
                book_data["matchScore"] = 0.5

            scored_books.append(book_data)

        scored_books.sort(key=lambda x: x.get("matchScore", 0), reverse=True)

        sections.append(
            {
                "author": author,
                "books": scored_books[:books_per_author],
                "user_preference_score": author_info["score"],
            }
        )

    return sections


# This content should be APPENDED to discovery_endpoints_part1.py

# Continue from part 1...


@router.get("/similar-readers")
async def get_similar_readers_books(
    limit: int = Query(15, ge=5, le=30),
    similarity_threshold: float = Query(
        0.3,  # ← OBNIŻONE z 0.5 do 0.3 dla nowych użytkowników
        ge=0.1,
        le=0.9,
        description="Próg podobieństwa (0.1-0.9)",
    ),
    current_user=Depends(get_current_user),
):
    """SEKCJA B: Książki popularne wśród podobnych czytelników"""
    db = get_database()
    user_id = str(current_user.id)

    logger.info(
        f"👥 /similar-readers called for user: {user_id}, threshold: {similarity_threshold}"
    )

    try:
        lightgcn = get_service()
        user_idx = lightgcn.mongo_user_to_idx.get(user_id)

        if user_idx is None:
            logger.warning(f"⚠️ User {user_id} not in LightGCN model")
            return await _similar_readers_fallback(
                db, user_id, limit, reason="user_not_in_lightgcn_model"
            )

        user_embedding = lightgcn.user_emb[user_idx]
        logger.info(f"✅ Got embedding for user_idx: {user_idx}")
    except Exception as e:
        logger.error(f"❌ LightGCN service error: {e}")
        return await _similar_readers_fallback(db, user_id, limit, reason="lightgcn_unavailable")

    # Znajdź podobnych użytkowników
    user_query_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
    all_users = await db.users.find({"_id": {"$ne": user_query_id}}).to_list(length=None)

    logger.info(f"📊 Found {len(all_users)} other users in database")

    if len(all_users) < 3:
        logger.warning(f"⚠️ Only {len(all_users)} users - recommend at least 5")

    similar_users = []
    similarities_calculated = 0

    # 🔍 DIAGNOSTIC: Track similarity scores distribution
    all_similarities = []
    users_with_embeddings = 0
    users_without_embeddings = 0

    for user in all_users:
        other_id = str(user["_id"])
        other_idx = lightgcn.mongo_user_to_idx.get(other_id)

        if other_idx is not None:
            users_with_embeddings += 1
            try:
                other_embedding = lightgcn.user_emb[other_idx]

                # 🔍 DIAGNOSTIC: Check embedding validity
                user_vector = _to_numpy_vector(user_embedding)
                other_vector = _to_numpy_vector(other_embedding)
                user_norm = np.linalg.norm(user_vector) if user_vector is not None else 0
                other_norm = np.linalg.norm(other_vector) if other_vector is not None else 0
                similarity = _safe_cosine(user_embedding, other_embedding)
                if similarity is None:
                    continue

                similarities_calculated += 1
                all_similarities.append(similarity)

                # 🔍 DIAGNOSTIC: Log first 5 similarities
                if similarities_calculated <= 5:
                    logger.info(
                        f"🔍 User {similarities_calculated}: similarity={similarity:.4f}, "
                        f"user_norm={user_norm:.2f}, other_norm={other_norm:.2f}"
                    )

                if similarity > similarity_threshold:
                    similar_users.append({"user_id": other_id, "similarity": similarity})
            except Exception as e:
                logger.debug(f"Similarity calc failed for {other_id}: {e}")
                continue
        else:
            users_without_embeddings += 1

    # 🔍 DIAGNOSTIC: Similarity statistics
    if all_similarities:
        logger.info(f"📊 SIMILARITY STATS:")
        logger.info(f"   Min: {min(all_similarities):.4f}")
        logger.info(f"   Max: {max(all_similarities):.4f}")
        logger.info(f"   Mean: {np.mean(all_similarities):.4f}")
        logger.info(f"   Median: {np.median(all_similarities):.4f}")
        logger.info(f"   Std: {np.std(all_similarities):.4f}")

        # Count by ranges
        ranges = {
            "0.0-0.1": sum(1 for s in all_similarities if 0.0 <= s < 0.1),
            "0.1-0.2": sum(1 for s in all_similarities if 0.1 <= s < 0.2),
            "0.2-0.3": sum(1 for s in all_similarities if 0.2 <= s < 0.3),
            "0.3-0.4": sum(1 for s in all_similarities if 0.3 <= s < 0.4),
            "0.4-0.5": sum(1 for s in all_similarities if 0.4 <= s < 0.5),
            "0.5-0.6": sum(1 for s in all_similarities if 0.5 <= s < 0.6),
            "0.6-0.7": sum(1 for s in all_similarities if 0.6 <= s < 0.7),
            "0.7+": sum(1 for s in all_similarities if s >= 0.7),
        }
        logger.info(f"📊 SIMILARITY DISTRIBUTION:")
        for range_name, count in ranges.items():
            percentage = (count / len(all_similarities)) * 100
            logger.info(f"   {range_name}: {count} users ({percentage:.1f}%)")

    logger.info(
        f"📊 EMBEDDING STATS: {users_with_embeddings} with embeddings, "
        f"{users_without_embeddings} without"
    )

    similar_users.sort(key=lambda x: x["similarity"], reverse=True)
    top_similar = similar_users[:50]

    logger.info(
        f"✅ Found {len(top_similar)} similar users from {similarities_calculated} comparisons "
        f"(threshold: {similarity_threshold})"
    )

    if top_similar:
        top_5_scores = [u["similarity"] for u in top_similar[:5]]
        logger.info(f"📊 Top 5 similarity scores: {top_5_scores}")

    if not top_similar:
        logger.warning(f"⚠️ No similar users found (threshold: {similarity_threshold})")
        return await _similar_readers_fallback(
            db, user_id, limit, reason="no_users_above_similarity_threshold"
        )

    # Pobierz książki które oni wypożyczyli
    similar_user_ids = [u["user_id"] for u in top_similar]

    similar_borrows = await db.interactions.find(
        {"user_id": {"$in": similar_user_ids}, "interaction_type": {"$in": ["borrow", "review"]}}
    ).to_list(length=None)

    logger.info(f"📚 Found {len(similar_borrows)} borrows from similar users")

    # Zlicz popularność
    book_popularity = Counter([b["book_id"] for b in similar_borrows])

    # Wyklucz już wypożyczone
    user_borrows = await db.interactions.find(
        {"user_id": user_id, "interaction_type": {"$in": ["borrow", "review"]}}
    ).to_list(length=None)
    borrowed_book_ids = {i["book_id"] for i in user_borrows}

    logger.info(f"🚫 User has {len(borrowed_book_ids)} borrowed books to exclude")

    # Filtruj
    ranked_books = [
        (book_id, count)
        for book_id, count in book_popularity.most_common()
        if book_id not in borrowed_book_ids
    ][:limit]

    logger.info(f"🎯 Got {len(ranked_books)} candidate books")

    if not ranked_books:
        logger.warning("⚠️ No books after filtering")
        return await _similar_readers_fallback(
            db, user_id, limit, reason="similar_users_have_no_new_books"
        )

    # Pobierz szczegóły
    book_ids = [book_id for book_id, _ in ranked_books]
    book_ids_obj = [_to_book_query_id(bid) for bid in book_ids]
    books = await db.books.find({"_id": {"$in": book_ids_obj}}).to_list(length=None)

    logger.info(f"📖 Fetched {len(books)} book details")

    book_dict = {str(b["_id"]): normalize_book(serialize_doc(b)) for b in books}
    max_count = ranked_books[0][1] if ranked_books else 1

    result_books = []
    for book_id, count in ranked_books:
        book_id_str = str(book_id)
        if book_id_str in book_dict:
            book = book_dict[book_id_str]
            book["popularityScore"] = count / max_count
            book["popularityCount"] = count

            # Dodaj matchScore z LightGCN
            try:
                gb_id = book.get("goodbooks_book_id")
                book_idx = lightgcn.book_id_to_item_idx.get(int(gb_id)) if gb_id else None

                if book_idx is not None:
                    book_embedding = lightgcn.item_emb[book_idx]
                    score = _safe_cosine(user_embedding, book_embedding)
                    if score is not None:
                        book["matchScore"] = score
            except:
                pass

            result_books.append(book)

    if not result_books:
        return await _similar_readers_fallback(
            db, user_id, limit, reason="similar_reader_books_not_found"
        )

    logger.info(f"✅ Returning {len(result_books)} books from {len(top_similar)} similar users")

    return {
        "books": result_books,
        "similar_user_count": len(top_similar),
        "metadata": {
            "fallback_used": False,
            "source": "lightgcn_user_similarity",
            "similarity_threshold": similarity_threshold,
            "total_users_checked": len(all_users),
            "users_with_embeddings": similarities_calculated,
            "similar_users_found": len(top_similar),
            "total_borrows": len(similar_borrows),
        },
    }


@router.get("/new-arrivals")
async def get_new_arrivals(
    limit: int = Query(20, ge=5, le=50),
    days: int = Query(30, ge=7, le=90),
    current_user=Depends(get_current_user),
):
    """SEKCJA C: Nowości w bibliotece"""
    db = get_database()
    user_id = str(current_user.id)

    cutoff_date = datetime.now() - timedelta(days=days)

    # Spróbuj znaleźć nowe książki
    new_books = await db.books.find({"created_at": {"$gte": cutoff_date}}).to_list(length=100)

    # Fallback: ostatnio dodane (po _id)
    if not new_books:
        new_books = await db.books.find().sort("_id", -1).limit(limit).to_list(length=None)

    # Profil użytkownika
    user_profile = {
        "favorite_genres": await get_user_top_genres(db, user_id, limit=5),
        "favorite_authors": await get_user_favorite_authors(db, user_id, limit=5),
    }

    # Oblicz similarity
    scored_books = []
    for book in new_books:
        book_data = normalize_book(serialize_doc(book))
        score = calculate_content_similarity(book_data, user_profile)
        book_data["matchScore"] = score
        book_data["coldStart"] = True
        book_data["similarityMethod"] = "content-based"
        scored_books.append(book_data)

    scored_books.sort(key=lambda x: x["matchScore"], reverse=True)
    return scored_books[:limit]


@router.get("/hidden-gems")
async def get_hidden_gems(
    limit: int = Query(15, ge=5, le=30),
    current_user=Depends(get_current_user),
):
    """SEKCJA C: Ukryte skarby 💎"""
    db = get_database()
    user_id = str(current_user.id)

    # Ulubione gatunki
    user_genres = await get_user_top_genres(db, user_id, limit=5)
    favorite_genres = [g["genre"] for g in user_genres]

    # Zlicz wypożyczenia
    borrow_counts = await db.interactions.aggregate(
        [
            {"$match": {"interaction_type": "borrow"}},
            {"$group": {"_id": "$book_id", "borrow_count": {"$sum": 1}}},
            {"$match": {"borrow_count": {"$lt": 50}}},
        ]
    ).to_list(length=None)

    underrated_book_ids = [
        ObjectId(b["_id"])
        for b in borrow_counts
        if isinstance(b.get("_id"), str) and ObjectId.is_valid(b["_id"])
    ]

    # Znajdź wysoko oceniane
    query = {
        "_id": {"$in": underrated_book_ids},
        "average_rating": {"$gte": 4.0},
        "available_copies": {"$gt": 0},
    }

    if favorite_genres:
        query["$or"] = [
            {"genre": {"$in": favorite_genres}},
            {"genres": {"$in": favorite_genres}},
        ]

    hidden_gems = await db.books.find(query).to_list(length=100)

    if not hidden_gems:
        # Fallback
        hidden_gems = (
            await db.books.find({"average_rating": {"$gte": 4.0}, "available_copies": {"$gt": 0}})
            .limit(50)
            .to_list(length=None)
        )

    # Personalizuj
    user_profile = {
        "favorite_genres": user_genres,
        "favorite_authors": await get_user_favorite_authors(db, user_id, limit=5),
    }

    scored_gems = []
    for book in hidden_gems:
        book_data = normalize_book(serialize_doc(book))

        borrow_info = next((b for b in borrow_counts if b["_id"] == book["_id"]), None)
        book_data["borrow_count"] = borrow_info["borrow_count"] if borrow_info else 0

        book_data["matchScore"] = calculate_content_similarity(book_data, user_profile)
        book_data["hiddenGem"] = True

        scored_gems.append(book_data)

    scored_gems.sort(key=lambda x: (x["matchScore"], x.get("average_rating", 0)), reverse=True)

    return scored_gems[:limit]


@router.get("/highly-rated")
async def get_highly_rated_discoveries(
    limit: int = Query(15, ge=5, le=30),
    min_rating: float = Query(4.5, ge=3.0, le=5.0),
    current_user=Depends(get_current_user),
):
    """SEKCJA C: Wysoko oceniane odkrycia ⭐"""
    db = get_database()
    user_id = str(current_user.id)

    # Ulubione gatunki
    user_genres = await get_user_top_genres(db, user_id, limit=5)
    favorite_genres = [g["genre"] for g in user_genres]

    # Przeczytane książki
    user_reads = await db.interactions.find(
        {"user_id": user_id, "interaction_type": {"$in": ["borrow", "review"]}}
    ).to_list(length=None)
    read_book_ids = [
        ObjectId(i["book_id"])
        for i in user_reads
        if isinstance(i.get("book_id"), str) and ObjectId.is_valid(i["book_id"])
    ]

    # Znajdź wysoko oceniane
    query = {
        "average_rating": {"$gte": min_rating},
        "available_copies": {"$gt": 0},
        "_id": {"$nin": read_book_ids},
    }

    if favorite_genres:
        query["$or"] = [
            {"genre": {"$in": favorite_genres}},
            {"genres": {"$in": favorite_genres}},
        ]

    highly_rated = await db.books.find(query).limit(100).to_list(length=None)

    if not highly_rated:
        # Fallback
        highly_rated = (
            await db.books.find(
                {"average_rating": {"$gte": min_rating}, "available_copies": {"$gt": 0}}
            )
            .limit(50)
            .to_list(length=None)
        )

    # Personalizuj z LightGCN
    try:
        lightgcn = get_service()
        user_idx = lightgcn.mongo_user_to_idx.get(user_id)
        user_embedding = lightgcn.user_emb[user_idx] if user_idx is not None else None
    except:
        user_embedding = None

    scored_books = []
    for book in highly_rated:
        book_data = normalize_book(serialize_doc(book))

        # LightGCN score
        if user_embedding is not None:
            try:
                gb_id = book.get("goodbooks_book_id")
                book_idx = lightgcn.book_id_to_item_idx.get(int(gb_id)) if gb_id else None

                if book_idx is not None:
                    book_embedding = lightgcn.item_emb[book_idx]
                    score = np.dot(user_embedding, book_embedding) / (
                        np.linalg.norm(user_embedding) * np.linalg.norm(book_embedding)
                    )
                    book_data["matchScore"] = float(score)
                else:
                    book_data["matchScore"] = 0.5
            except:
                book_data["matchScore"] = 0.5
        else:
            book_data["matchScore"] = 0.5

        book_data["highlyRated"] = True
        scored_books.append(book_data)

    # Hybrid: 70% matchScore + 30% rating
    scored_books.sort(
        key=lambda x: (x["matchScore"] * 0.7 + (x.get("average_rating", 0) / 5.0) * 0.3),
        reverse=True,
    )

    return scored_books[:limit]


@router.get("/diversity-comparison")
async def compare_diversity_metrics(
    n: int = Query(default=30, ge=10, le=50),
    lambda_values: str = Query(
        default="0.3,0.5,0.7,0.9", description="Wartości λ oddzielone przecinkami"
    ),
    current_user=Depends(get_current_user),
):
    """📊 Porównuje metryki różnorodności dla różnych wartości λ"""
    if not MMR_AVAILABLE:
        raise HTTPException(503, "MMR not available")

    db = get_database()
    user_id = str(current_user.id)

    # Parse lambda values
    try:
        lambdas = [float(x.strip()) for x in lambda_values.split(",")]
    except:
        raise HTTPException(400, "Invalid lambda_values format")

    # Zbierz wypożyczone
    borrowed_goodbooks_ids = set()
    async for loan in db.loans.find({"user_id": user_id, "status": "active"}):
        book_id = (
            ObjectId(loan.get("book_id"))
            if isinstance(loan.get("book_id"), str)
            else loan.get("book_id")
        )
        book = await db.books.find_one({"_id": book_id})
        if book and book.get("goodbooks_book_id"):
            try:
                borrowed_goodbooks_ids.add(int(book["goodbooks_book_id"]))
            except:
                pass

    # Pobierz kandydatów
    try:
        rec_ids = get_service().get_recommendations_for_user(
            mongo_user_id=user_id,
            n=n * 3,
            exclude_goodbooks_ids=borrowed_goodbooks_ids,
            use_cache=False,
        )
    except:
        raise HTTPException(500, "Failed to get recommendations")

    candidates = await enrich_recommendations_with_metadata(rec_ids, db, limit=n * 3)

    # Test każdego λ
    results = []

    for lam in lambdas:
        recs = mmr_rerank(
            candidates, n=n, lambda_param=lam, enforce_author_limit=True, max_per_author=2
        )

        metrics = diversity_metrics(recs)

        results.append(
            {
                "lambda": lam,
                "metrics": metrics,
                "sample_books": [
                    {
                        "title": r.get("title"),
                        "author": r.get("author"),
                        "genres": r.get("genres", [])[:2],
                    }
                    for r in recs[:5]
                ],
            }
        )

    return {
        "comparison": results,
        "recommendation": "Wyższa entropia i dissimilarity = większa różnorodność",
    }
