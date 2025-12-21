"""
models/dependencies.py
Dependency injection dla FastAPI
"""

import logging
from typing import Optional

from ..database import get_database
from ..service.interaction_service import InteractionService
from ..service.lightgcn_adapter import LightGCNAdapter

# Import singletona serwisu LightGCN
import recommendation_engine.goodbooks_lightgcn_service as service_module

logger = logging.getLogger(__name__)


async def get_interaction_service() -> InteractionService:
    """
    Dependency injection dla InteractionService

    Tworzy InteractionService podłączony do GoodbooksLightGCNService
    przez adapter
    """
    db = get_database()

    # Pobierz singleton GoodbooksLightGCNService (zainicjalizowany w main.py)
    lightgcn_service = service_module.goodbooks_lgcn_service

    if lightgcn_service is None:
        logger.warning(
            "⚠️  GoodbooksLightGCNService not initialized - "
            "InteractionService will work WITHOUT embedding updates"
        )
        # Zwróć InteractionService bez rec_service (embeddingi nie będą aktualizowane)
        return InteractionService(
            interactions_collection=db.interactions,
            recommendation_service=None,  # Brak serwisu rekomendacji
        )

    # Stwórz adapter
    adapter = LightGCNAdapter(lightgcn_service, db)

    # Stwórz InteractionService z adapterem
    return InteractionService(
        interactions_collection=db.interactions,
        recommendation_service=adapter,  # Adapter zamiast starego RecommendationService!
    )


# Opcjonalnie: dependency dla samego adaptera (jeśli potrzebne gdzie indziej)
async def get_lightgcn_adapter() -> Optional[LightGCNAdapter]:
    """
    Dependency injection dla LightGCNAdapter
    """
    db = get_database()
    lightgcn_service = service_module.goodbooks_lgcn_service

    if lightgcn_service is None:
        return None

    return LightGCNAdapter(lightgcn_service, db)
