"""
services/recommendation_service.py
LightGCN-based recommendation service
Czyta z kolekcji 'interactions' (view, review, borrow)
"""
import torch
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class RecommendationService:
    """
    LightGCN recommendation service
    - Czyta z kolekcji 'interactions'
    - Uwzględnia wszystkie typy: view (0.3), review (0.8), borrow (1.0)
    - Historia wypożyczeń (borrow) ma najwyższą wagę
    """
    
    def __init__(self, db):
        self.db = db
        self.model = None  # Twój LightGCN model
        self.user_embeddings = {}
        self.book_embeddings = {}
        self.user_id_map = {}  # user_id -> index
        self.book_id_map = {}  # book_id -> index
        self.learning_rate = 0.01
    
    async def load_model(self, model_path: str = "models/lightgcn_model.pth"):
        """Ładuje wytrenowany model LightGCN"""
        try:
            checkpoint = torch.load(model_path)
            self.model = checkpoint['model']
            self.user_embeddings = checkpoint['user_embeddings']
            self.book_embeddings = checkpoint['book_embeddings']
            self.user_id_map = checkpoint['user_id_map']
            self.book_id_map = checkpoint['book_id_map']
            
            logger.info(f"✅ Model loaded: {len(self.user_id_map)} users, {len(self.book_id_map)} books")
            
        except Exception as e:
            logger.error(f"❌ Model loading failed: {str(e)}")
            raise
    
    async def prepare_training_data(self) -> tuple:
        """
        Przygotowuje dane z kolekcji 'interactions'
        Uwzględnia WSZYSTKIE typy interakcji z wagami
        """
        # Pobierz wszystkie interakcje
        interactions = await self.db.interactions.find({}).to_list(length=None)
        
        logger.info(f"📊 Preparing training data from {len(interactions)} interactions")
        
        # Grupuj według typu
        by_type = {}
        for inter in interactions:
            itype = inter.get("interaction_type", "unknown")
            by_type[itype] = by_type.get(itype, 0) + 1
        
        logger.info(f"📊 Interactions by type: {by_type}")
        
        # Stwórz edge list z wagami
        edges = []
        for inter in interactions:
            user_id = inter.get("user_id")
            book_id = inter.get("book_id")
            weight = inter.get("weight", 0.5)
            
            if user_id and book_id:
                edges.append({
                    "user_id": user_id,
                    "book_id": book_id,
                    "weight": weight,
                    "timestamp": inter.get("created_at")
                })
        
        logger.info(f"✅ Prepared {len(edges)} weighted edges for training")
        
        return edges
    
    async def update_user_embedding_incremental(
        self,
        user_id: str,
        book_id: str,
        interaction_weight: float
    ):
        """
        Incremental update using SGD
        Waga interaction_weight:
        - 0.3 dla view
        - 0.8 dla review
        - 1.0 dla borrow (historia wypożyczeń!)
        """
        try:
            # Pobierz obecne embeddingi
            user_idx = self.user_id_map.get(user_id)
            book_idx = self.book_id_map.get(book_id)
            
            if user_idx is None or book_idx is None:
                logger.warning(f"⚠️ User or book not in training set: {user_id}, {book_id}")
                return
            
            user_emb = self.user_embeddings[user_idx]
            book_emb = self.book_embeddings[book_idx]
            
            # SGD update z wagą
            # Gradient: weight * (book_embedding - user_embedding)
            gradient = interaction_weight * (book_emb - user_emb)
            
            # Update user embedding
            self.user_embeddings[user_idx] = user_emb + self.learning_rate * gradient
            
            logger.info(
                f"✅ Embedding updated: User {user_id} | "
                f"Book {book_id} | Weight: {interaction_weight}"
            )
            
        except Exception as e:
            logger.error(f"❌ Incremental update failed: {str(e)}")
            raise
    
    async def get_recommendations(
        self,
        user_id: str,
        top_k: int = 10,
        exclude_interacted: bool = True
    ) -> List[Dict]:
        """
        Generuje rekomendacje dla użytkownika
        Uwzględnia całą historię interakcji (view, review, borrow)
        """
        try:
            user_idx = self.user_id_map.get(user_id)
            
            if user_idx is None:
                logger.warning(f"⚠️ User not in training set: {user_id}")
                return await self._get_popular_books(top_k)
            
            # Pobierz embedding użytkownika
            user_emb = self.user_embeddings[user_idx]
            
            # Oblicz similarity ze wszystkimi książkami
            scores = {}
            for book_id, book_idx in self.book_id_map.items():
                book_emb = self.book_embeddings[book_idx]
                
                # Cosine similarity
                score = np.dot(user_emb, book_emb) / (
                    np.linalg.norm(user_emb) * np.linalg.norm(book_emb) + 1e-8
                )
                scores[book_id] = float(score)
            
            # Opcjonalnie: wyklucz książki z którymi user już interakcjonował
            if exclude_interacted:
                user_interactions = await self.db.interactions.find(
                    {"user_id": user_id}
                ).to_list(length=None)
                
                interacted_books = {inter["book_id"] for inter in user_interactions}
                scores = {k: v for k, v in scores.items() if k not in interacted_books}
            
            # Sortuj i weź top-K
            sorted_books = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            top_books = sorted_books[:top_k]
            
            # Pobierz szczegóły książek
            recommendations = []
            for book_id, score in top_books:
                book = await self.db.books.find_one({"_id": book_id})
                if book:
                    recommendations.append({
                        "book_id": book_id,
                        "title": book.get("title"),
                        "authors": book.get("authors"),
                        "score": score,
                        "image_url": book.get("image_url")
                    })
            
            logger.info(f"✅ Generated {len(recommendations)} recommendations for {user_id}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Recommendation generation failed: {str(e)}")
            return await self._get_popular_books(top_k)
    
    async def _get_popular_books(self, top_k: int = 10) -> List[Dict]:
        """Fallback: zwraca popularne książki"""
        cursor = self.db.books.find({}).sort("ratings_count", -1).limit(top_k)
        books = await cursor.to_list(length=top_k)
        
        return [{
            "book_id": str(book["_id"]),
            "title": book.get("title"),
            "authors": book.get("authors"),
            "score": 0.0,
            "image_url": book.get("image_url")
        } for book in books]
    
    async def get_interaction_stats(self, user_id: str) -> Dict:
        """
        Statystyki interakcji użytkownika
        Pokazuje ile ma view, review, borrow
        """
        interactions = await self.db.interactions.find(
            {"user_id": user_id}
        ).to_list(length=None)
        
        stats = {
            "total": len(interactions),
            "view": 0,
            "review": 0,
            "borrow": 0
        }
        
        for inter in interactions:
            itype = inter.get("interaction_type")
            if itype in stats:
                stats[itype] += 1
        
        return stats