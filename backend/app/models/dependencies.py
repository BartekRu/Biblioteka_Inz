from ..service.interaction_service import InteractionService
from ..service.recommendation_service import RecommendationService
from ..database import get_database


async def get_interaction_service() -> InteractionService:
    """DI: InteractionService"""
    db = get_database()
    rec_service = RecommendationService(db)

    # Załaduj model (opcjonalnie, jeśli już wytrenowany)
    try:
        await rec_service.load_model()
    except:
        pass  # Model nie załadowany - będzie fallback

    return InteractionService(
        interactions_collection=db.interactions, recommendation_service=rec_service
    )


async def get_recommendation_service() -> RecommendationService:
    """DI: RecommendationService"""
    db = await get_database()
    rec_service = RecommendationService(db)

    try:
        await rec_service.load_model()
    except:
        pass

    return rec_service
