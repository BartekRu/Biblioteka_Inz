from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema





class User(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)

    email: EmailStr
    username: str
    full_name: str
    role: str = "user"  # user, librarian, admin
    is_active: bool = True

    # ID użytkownika z goodbooks-10k (1–53424) – opcjonalne
    goodbooks_user_id: Optional[int] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Preferencje pod rekomendacje
    favorite_genres: List[str] = []
    favorite_authors: List[str] = []
    reading_history: List[str] = []  # np. listę ID książek (ObjectId jako string)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "email": "jan.kowalski@example.com",
                "username": "jkowalski",
                "full_name": "Jan Kowalski",
                "role": "user",
                "goodbooks_user_id": 1234,
                "favorite_genres": ["Fantasy", "Science Fiction"],
                "favorite_authors": ["Andrzej Sapkowski", "Stanisław Lem"],
            }
        }


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str
    role: str = "user"
    goodbooks_user_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "jan.kowalski@example.com",
                "username": "jkowalski",
                "password": "SecurePassword123!",
                "full_name": "Jan Kowalski",
                "role": "user",
                "goodbooks_user_id": 1234,
            }
        }


class UserInDB(User):
    hashed_password: str


class UserResponse(BaseModel):
    id: str = Field(alias="_id")

    email: EmailStr
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    goodbooks_user_id: Optional[int] = None
    favorite_genres: List[str] = []
    favorite_authors: List[str] = []
    reading_history: List[str] = []

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "email": "jan.kowalski@example.com",
                "username": "jkowalski",
                "full_name": "Jan Kowalski",
                "role": "user",
                "is_active": True,
                "created_at": "2024-01-01T12:00:00",
                "goodbooks_user_id": 1234,
                "favorite_genres": ["Fantasy"],
                "favorite_authors": ["Andrzej Sapkowski"],
                "reading_history": ["60c72b2f9b1d8b3a2c3e1f1a"],
            }
        }


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    favorite_genres: Optional[List[str]] = None
    favorite_authors: Optional[List[str]] = None
    goodbooks_user_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Jan Maria Kowalski",
                "favorite_genres": ["Fantasy", "Horror"],
                "favorite_authors": ["Andrzej Sapkowski", "Stephen King"],
                "goodbooks_user_id": 2345,
            }
        }
