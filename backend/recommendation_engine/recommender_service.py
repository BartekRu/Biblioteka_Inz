import torch
import numpy as np
import json
from pathlib import Path

class RecommenderService:
    def __init__(self):
        self.user_embeddings = None
        self.item_embeddings = None
        self.book_mapping = None
        self.user_mapping = None
        self.is_loaded = False
    
    def load(self, model_dir: str = "recommendation_engine"):
        """Załaduj wytrenowany model"""
        model_dir = Path(model_dir)
        
        checkpoint_path = model_dir / "trained_models" / "goodbooks_lightgcn_best.pt"
        print(f"Ładowanie modelu z {checkpoint_path}...")
        
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        self.user_embeddings = checkpoint['user_emb'].numpy()
        self.item_embeddings = checkpoint['item_emb'].numpy()
        
        with open(model_dir / "data" / "processed" / "book_mapping.json") as f:
            self.book_mapping = json.load(f)
        
        with open(model_dir / "data" / "processed" / "user_mapping.json") as f:
            self.user_mapping = json.load(f)
        
        self.is_loaded = True
        print(f"✅ Model załadowany!")
        print(f"   Users: {self.user_embeddings.shape[0]}")
        print(f"   Books: {self.item_embeddings.shape[0]}")
        
        return self
    
    def get_recommendations(
        self, 
        user_idx: int, 
        n: int = 10, 
        exclude_books: list = None
    ) -> list:
        """
        Rekomendacje dla użytkownika (po indeksie wewnętrznym)
        """
        if not self.is_loaded:
            raise RuntimeError("Model nie załadowany! Wywołaj load() najpierw.")
        
        if user_idx >= len(self.user_embeddings):
            return []
        
        scores = self.user_embeddings[user_idx] @ self.item_embeddings.T
        
        if exclude_books:
            for book_idx in exclude_books:
                if book_idx < len(scores):
                    scores[book_idx] = -np.inf
        
        top_indices = np.argsort(scores)[-n:][::-1]
        
        recommendations = []
        for idx in top_indices:
            original_book_id = self.book_mapping['to_original'].get(str(idx))
            if original_book_id:
                recommendations.append({
                    'book_id': int(original_book_id),
                    'score': float(scores[idx])
                })
        
        return recommendations
    
    def get_similar_books(self, book_idx: int, n: int = 10) -> list:
        """
        Znajdź podobne książki (cosine similarity)
        """
        if not self.is_loaded:
            raise RuntimeError("Model nie załadowany!")
        
        if book_idx >= len(self.item_embeddings):
            return []
        
        book_emb = self.item_embeddings[book_idx]
        
        norms = np.linalg.norm(self.item_embeddings, axis=1)
        similarities = (self.item_embeddings @ book_emb) / (norms * np.linalg.norm(book_emb) + 1e-10)
        
        similarities[book_idx] = -np.inf
        
        top_indices = np.argsort(similarities)[-n:][::-1]
        
        similar = []
        for idx in top_indices:
            original_book_id = self.book_mapping['to_original'].get(str(idx))
            if original_book_id:
                similar.append({
                    'book_id': int(original_book_id),
                    'similarity': float(similarities[idx])
                })
        
        return similar


_recommender = None

def get_recommender() -> RecommenderService:
    global _recommender
    if _recommender is None:
        _recommender = RecommenderService().load()
    return _recommender