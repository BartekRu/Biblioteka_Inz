"""
Interaction Model - Model interakcji użytkownika z książkami

Przechowuje wszystkie interakcje (wypożyczenia, recenzje, przeglądania)
dla systemu rekomendacji LightGCN.

UWAGA: Uproszczona wersja bez PyObjectId - używamy string dla _id
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


class InteractionBase(BaseModel):
    """Bazowy model interakcji"""

    user_id: str = Field(..., description="ID użytkownika MongoDB")
    book_id: str = Field(..., description="ID książki MongoDB")
    interaction_type: str = Field(..., description="Typ: 'borrow', 'review', 'view', 'reserve'")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Ocena 1-5 (dla review)")
    weight: float = Field(
        default=1.0, description="Waga interakcji: borrow=1.0, review=0.8, view=0.3"
    )
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class InteractionCreate(InteractionBase):
    """Model do tworzenia nowej interakcji"""

    pass


class InteractionInDB(InteractionBase):
    """Model interakcji w bazie danych"""

    id: Optional[str] = Field(default=None, alias="_id")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class InteractionResponse(BaseModel):
    """Odpowiedź API dla interakcji"""

    id: str = Field(alias="_id")
    user_id: str
    book_id: str
    interaction_type: str
    rating: Optional[int] = None
    weight: float
    timestamp: datetime

    model_config = ConfigDict(populate_by_name=True)


# Wagi dla różnych typów interakcji
INTERACTION_WEIGHTS = {
    "borrow": 1.0,  # Wypożyczenie - najsilniejszy sygnał
    "review": 0.8,  # Recenzja - silny sygnał
    "reserve": 0.6,  # Rezerwacja - średni sygnał
    "view": 0.1,  # Przegladanie - bardzo slaby sygnal
    "favorite": 0.9,  # Dodanie do ulubionych
    "search": 0.2,  # Wyszukiwanie - bardzo slaby sygnal
    "wishlist_add": 0.5,
    "wishlist_remove": 0.0,
}


def get_interaction_weight(interaction_type: str) -> float:
    """Pobierz wagę dla typu interakcji"""
    return INTERACTION_WEIGHTS.get(interaction_type.lower(), 0.5)
