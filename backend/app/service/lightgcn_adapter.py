"""
services/lightgcn_adapter.py
Adapter łączący InteractionService z GoodbooksLightGCNService
Obsługuje konwersję MongoDB book_id -> goodbooks_book_id
"""
import logging
from typing import Optional
from bson import ObjectId

logger = logging.getLogger(__name__)


class LightGCNAdapter:
    """
    Adapter dla GoodbooksLightGCNService do użycia w InteractionService
    
    Rozwiązuje problem:
    - InteractionService pracuje z MongoDB book_id (ObjectId string)
    - GoodbooksLightGCNService wymaga goodbooks_book_id (int)
    """
    
    def __init__(self, lightgcn_service, db):
        """
        Args:
            lightgcn_service: Instancja GoodbooksLightGCNService
            db: MongoDB database handle
        """
        self.lightgcn = lightgcn_service
        self.db = db
        self._goodbooks_cache = {}  # Cache: mongo_id -> goodbooks_id
        
    async def update_user_embedding_incremental(
        self,
        user_id: str,
        book_id: str,
        interaction_weight: float
    ):
        """
        Aktualizuje embedding użytkownika po nowej interakcji
        
        Args:
            user_id: MongoDB user_id (ObjectId string)
            book_id: MongoDB book_id (ObjectId string)
            interaction_weight: Waga interakcji (0.3, 0.8, 1.0)
        
        Returns:
            Dict z wynikami aktualizacji
        """
        try:
            # 1. Konwersja book_id -> goodbooks_book_id
            goodbooks_id = await self._get_goodbooks_id(book_id)
            
            if goodbooks_id is None:
                logger.warning(
                    f"⚠️  Book {book_id} nie ma goodbooks_book_id - pomijam update embeddingu"
                )
                return {
                    "success": False,
                    "reason": "book_not_in_goodbooks_dataset",
                    "book_id": book_id
                }
            
            # 2. Mapowanie interaction_weight -> interaction_type
            # (GoodbooksLightGCNService używa type zamiast weight)
            interaction_type = self._weight_to_type(interaction_weight)
            
            # 3. Wywołanie GoodbooksLightGCNService
            result = self.lightgcn.process_interaction(
                mongo_user_id=user_id,
                goodbooks_book_id=goodbooks_id,
                interaction_type=interaction_type
            )
            
            if result.get("success"):
                logger.info(
                    f"✅ Embedding updated: user={user_id[:12]}... "
                    f"book={book_id[:12]}... (goodbooks_id={goodbooks_id}) "
                    f"type={interaction_type}"
                )
            
            return result
            
        except Exception as e:
            logger.error(
                f"❌ Embedding update failed: user={user_id}, book={book_id}, error={e}"
            )
            return {
                "success": False,
                "reason": "exception",
                "error": str(e)
            }
    
    async def _get_goodbooks_id(self, mongo_book_id: str) -> Optional[int]:
        """
        Pobiera goodbooks_book_id z MongoDB dla danej książki
        Używa cache aby zminimalizować zapytania do DB
        """
        # Sprawdź cache
        if mongo_book_id in self._goodbooks_cache:
            return self._goodbooks_cache[mongo_book_id]
        
        try:
            # Konwersja string -> ObjectId
            book_key = ObjectId(mongo_book_id) if ObjectId.is_valid(mongo_book_id) else mongo_book_id
            
            # Zapytanie do MongoDB
            book = await self.db.books.find_one(
                {"_id": book_key},
                {"goodbooks_book_id": 1}
            )
            
            if not book:
                logger.warning(f"⚠️  Book {mongo_book_id} not found in database")
                return None
            
            goodbooks_id = book.get("goodbooks_book_id")
            
            if goodbooks_id is None:
                logger.warning(f"⚠️  Book {mongo_book_id} has no goodbooks_book_id field")
                return None
            
            # Konwersja do int
            try:
                goodbooks_id = int(goodbooks_id)
            except (TypeError, ValueError):
                logger.warning(
                    f"⚠️  Invalid goodbooks_book_id for {mongo_book_id}: {goodbooks_id}"
                )
                return None
            
            # Zapisz w cache
            self._goodbooks_cache[mongo_book_id] = goodbooks_id
            
            return goodbooks_id
            
        except Exception as e:
            logger.error(f"❌ Error getting goodbooks_id for {mongo_book_id}: {e}")
            return None
    
    @staticmethod
    def _weight_to_type(weight: float) -> str:
        """
        Konwertuje wagę interakcji na typ
        
        Wagi w InteractionService:
        - 0.3 = view
        - 0.8 = review
        - 1.0 = borrow
        """
        if weight >= 0.95:  # 1.0
            return "borrow"
        elif weight >= 0.7:  # 0.8
            return "review"
        elif weight >= 0.25:  # 0.3
            return "view"
        else:
            return "view"  # fallback