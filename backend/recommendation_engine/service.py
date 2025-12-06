# backend/app/recommendation_engine/service.py
from typing import List, Dict, Any


def get_recommendations_for_goodbooks_user(
    user_goodbooks_id: int,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Zwraca listę rekomendacji dla użytkownika goodbooks.
    Oczekiwany format wyniku:
        [{"book_id": <goodbooks_book_id:int>, "score": <float>}, ...]

    🔧 TODO:
    Tutaj wepnij swój LightGCN:
    - wczytaj wytrenowany model
    - wygeneruj rekomendacje dla `user_goodbooks_id`
    - zwróć listę dictów jak wyżej.

    Poniżej jest *tymczasowa* atrapa, żeby endpoint działał nawet
    bez gotowego silnika – zwraca pustą listę.
    """
    # PRZYKŁAD – do wywalenia gdy podłączysz LightGCN
    # return recommender.recommend_for_user(user_goodbooks_id, top_k=top_k)

    return []
