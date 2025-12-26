"""
Debug & Admin Endpoints Module
===============================

Debug and administrative endpoints:
- User stats
- Service stats
- Embedding stats
- Initialize new users
- Test endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import logging

from ..database import get_database
from .auth import get_current_user
from ..models.dependencies import get_interaction_service
from ..service.interaction_service import InteractionService

logger = logging.getLogger(__name__)

router = APIRouter()


# ==========================================================
#  HELPER: Get Service
# ==========================================================


def get_lightgcn_service():
    """Lazy load LightGCN service"""
    import recommendation_engine.goodbooks_lightgcn_service as service_module

    if service_module.goodbooks_lgcn_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return service_module.goodbooks_lgcn_service


# ==========================================================
#  USER DEBUG
# ==========================================================


@router.get("/debug/user-stats/{user_id}")
async def get_user_debug_stats(user_id: str, current_user=Depends(get_current_user)):
    """
    🔍 Debug - statystyki użytkownika

    Pokazuje:
    - Czy user ma embedding
    - Norma embeddingu
    - Liczba interakcji
    - Ostatnia aktualizacja
    """
    current_uid = str(getattr(current_user, "id", ""))
    is_admin = getattr(current_user, "role", "") == "admin"

    if user_id != current_uid and not is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        service = get_lightgcn_service()
        has_embedding = user_id in service.mongo_user_to_idx

        user_stats = {
            "user_id": user_id,
            "has_embedding": has_embedding,
            "user_idx": service.mongo_user_to_idx.get(user_id),
            "is_new_user": (
                has_embedding and service.mongo_user_to_idx[user_id] >= service.num_users
            ),
        }

        if has_embedding:
            user_idx = service.mongo_user_to_idx[user_id]
            embedding = service.user_emb[user_idx]

            import numpy as np

            user_stats["embedding_norm"] = float(np.linalg.norm(embedding))
            user_stats["embedding_mean"] = float(np.mean(embedding))
            user_stats["embedding_std"] = float(np.std(embedding))
            user_stats["interactions"] = service.user_interaction_counts.get(user_id, 0)

            last_update = service.user_last_update.get(user_id)
            if last_update:
                user_stats["last_update"] = last_update.isoformat()

        return user_stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================
#  SERVICE DEBUG
# ==========================================================


@router.get("/debug/service-stats")
async def get_service_stats(current_user=Depends(get_current_user)):
    """
    📊 Debug - statystyki serwisu (admin only)

    Pokazuje:
    - Total users w modelu
    - New users created
    - Total updates
    - Interactions since checkpoint
    """
    is_admin = getattr(current_user, "role", "") == "admin"

    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    try:
        stats = get_lightgcn_service().get_stats()

        # Check MMR availability
        try:
            from recommendation_engine.mmr_reranking import mmr_rerank

            stats["mmr_available"] = True
        except ImportError:
            stats["mmr_available"] = False

        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================
#  EMBEDDING STATS
# ==========================================================


@router.get("/embedding-stats")
async def get_embedding_stats(
    interaction_service: InteractionService = Depends(get_interaction_service),
):
    """
    💾 Statystyki aktualizacji embeddingów

    Pokazuje ile interakcji ma zaktualizowane embeddingi.
    """
    stats = await interaction_service.get_embedding_stats()

    # Dodaj statystyki z LightGCN
    try:
        service_stats = get_lightgcn_service().get_stats()
        stats["lightgcn_service"] = service_stats
    except Exception as e:
        stats["lightgcn_service"] = {"error": str(e)}

    return stats


# ==========================================================
#  ADMIN: INITIALIZE NEW USERS ⭐ FIXED!
# ==========================================================


@router.post("/admin/initialize-new-users")
async def initialize_new_users(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    🔧 ADMIN: Initialize embeddings for new users

    ✅ POPRAWIONY - używa serwisu zamiast nieistniejącego lightgcn_recommender

    Call this after:
    - Adding test users via populate_database.py
    - Manual user creation
    - Database imports

    Returns:
        {
            "message": "Success",
            "total_users": 1010,
            "new_users_initialized": 1000
        }
    """
    logger.info("🔧 Initializing embeddings for new users...")

    # Get all users from MongoDB
    all_users = await db.users.find({}).to_list(length=None)
    total_users = len(all_users)
    logger.info(f"📊 Found {total_users} users in MongoDB")

    # ✅ FIX: Użyj serwisu zamiast lightgcn_recommender
    try:
        service = get_lightgcn_service()
    except Exception as e:
        logger.error(f"❌ LightGCN service not available: {e}")
        raise HTTPException(
            status_code=503, detail="LightGCN service not initialized. Restart backend first."
        )

    users_with_embeddings = len(service.mongo_user_to_idx)
    logger.info(f"📊 Currently {users_with_embeddings} users have embeddings")

    # Find users without embeddings
    new_users = []
    for user in all_users:
        user_id = str(user["_id"])
        if user_id not in service.mongo_user_to_idx:
            new_users.append(user_id)

    if not new_users:
        logger.info("✅ All users already have embeddings!")
        return {
            "message": "All users already have embeddings",
            "total_users": total_users,
            "users_with_embeddings": users_with_embeddings,
            "new_users_initialized": 0,
        }

    logger.info(f"🆕 Found {len(new_users)} users without embeddings")

    # Initialize embeddings for new users
    initialized_count = 0

    for user_id in new_users:
        # Get user's interactions
        interactions = await db.interactions.find({"user_id": user_id}).to_list(length=None)

        if len(interactions) == 0:
            logger.debug(f"⚠️ User {user_id} has no interactions, skipping")
            continue

        # ✅ FIX: Użyj book_id_to_item_idx zamiast goodbooks_id_to_idx
        book_goodbooks_ids = []
        for interaction in interactions:
            book_id = interaction.get("book_id")
            if not book_id:
                continue

            # Konwertuj book_id na ObjectId
            book_id_obj = ObjectId(book_id) if isinstance(book_id, str) else book_id

            # Znajdź goodbooks_book_id
            book = await db.books.find_one({"_id": book_id_obj})
            if book and book.get("goodbooks_book_id"):
                try:
                    gb_id = int(book["goodbooks_book_id"])
                    # ✅ POPRAWKA: Użyj book_id_to_item_idx
                    if gb_id in service.book_id_to_item_idx:
                        book_goodbooks_ids.append(gb_id)
                except (TypeError, ValueError):
                    continue

        if not book_goodbooks_ids:
            logger.debug(f"⚠️ User {user_id} has no valid book interactions")
            continue

        # Initialize embedding based on their books
        try:
            import numpy as np

            # Get book embeddings (✅ POPRAWKA: użyj book_id_to_item_idx)
            book_indices = [service.book_id_to_item_idx[gb_id] for gb_id in book_goodbooks_ids]
            book_embeddings = service.item_emb[book_indices]

            # Average book embeddings as initial user embedding
            initial_embedding = np.mean(book_embeddings, axis=0)

            # ✅ FIX: Normalizuj embedding do podobnej normy jak bazowe embeddingi
            # Bazowe embeddingi użytkowników mają normę ~10-15
            target_norm = 10.0
            current_norm = np.linalg.norm(initial_embedding)

            if current_norm > 0.01:  # Unikaj dzielenia przez zero
                initial_embedding = initial_embedding * (target_norm / current_norm)

            logger.debug(
                f"User {user_id[:12]}: norm before={current_norm:.2f}, "
                f"after={np.linalg.norm(initial_embedding):.2f}"
            )

            # Add user to model mappings
            new_idx = len(service.mongo_user_to_idx)
            service.mongo_user_to_idx[user_id] = new_idx
            service.idx_to_mongo_user[new_idx] = user_id

            # Expand embedding arrays
            service.user_emb = np.vstack([service.user_emb, initial_embedding.reshape(1, -1)])

            initialized_count += 1

            if initialized_count % 100 == 0:
                logger.info(f"📊 Initialized {initialized_count}/{len(new_users)} users...")

        except Exception as e:
            logger.error(f"❌ Error initializing user {user_id}: {e}")
            continue

    logger.info(f"✅ Initialized {initialized_count} new users")

    # ✅ FIX: Zapisz WSZYSTKIE embeddingi do MongoDB!
    logger.info("💾 Saving embeddings to MongoDB...")
    saved_count = 0

    for user_id in new_users:
        if user_id not in service.mongo_user_to_idx:
            continue  # Nie został zainicjalizowany

        user_idx = service.mongo_user_to_idx[user_id]

        try:
            # Wywołaj metodę zapisu (async)
            await service._save_user_embedding_to_db(user_id, user_idx)
            saved_count += 1

            if saved_count % 100 == 0:
                logger.info(f"💾 Saved {saved_count}/{initialized_count} embeddings...")

        except Exception as e:
            logger.error(f"❌ Error saving embedding for {user_id}: {e}")
            continue

    logger.info(f"✅ Saved {saved_count} embeddings to MongoDB")

    return {
        "message": "Successfully initialized new users",
        "total_users": total_users,
        "users_with_embeddings": users_with_embeddings,
        "new_users_found": len(new_users),
        "new_users_initialized": initialized_count,
        "users_skipped": len(new_users) - initialized_count,
        "embeddings_saved_to_db": saved_count,  # ← NOWE!
    }


# ==========================================================
#  TEST ENDPOINT
# ==========================================================


@router.get("/test-new-endpoints")
async def test_new_endpoints(current_user=Depends(get_current_user)):
    """
    🧪 Test wszystkie nowe endpointy

    Returns counts for each endpoint type.
    """
    from .discovery_endpoints import (
        get_genre_recommendations,
        get_author_recommendations,
        get_similar_readers_books,
        get_new_arrivals,
        get_hidden_gems,
        get_highly_rated_discoveries,
    )

    results = {}

    try:
        results["by_genre"] = len(await get_genre_recommendations(1, 5, current_user))
        results["by_author"] = len(await get_author_recommendations(1, 5, current_user))

        similar = await get_similar_readers_books(5, 0.5, current_user)
        results["similar_readers"] = len(similar.get("books", []))

        results["new_arrivals"] = len(await get_new_arrivals(5, 30, current_user))
        results["hidden_gems"] = len(await get_hidden_gems(5, current_user))
        results["highly_rated"] = len(await get_highly_rated_discoveries(5, 4.5, current_user))

        results["status"] = "✅ All endpoints working!"
    except Exception as e:
        results["status"] = f"❌ Error: {str(e)}"
        results["error"] = str(e)

    return results
