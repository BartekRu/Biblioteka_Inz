from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class User(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    email: EmailStr
    username: str
    full_name: str
    role: str = "user"  # user, librarian, admin
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # User preferences for recommendations
    favorite_genres: List[str] = []
    favorite_authors: List[str] = []
    reading_history: List[str] = []  # List of book IDs
    
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
                "favorite_genres": ["Fantasy", "Science Fiction"],
                "favorite_authors": ["Andrzej Sapkowski", "Stanisław Lem"]
            }
        }


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str
    role: str = "user"
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "jan.kowalski@example.com",
                "username": "jkowalski",
                "password": "SecurePassword123!",
                "full_name": "Jan Kowalski",
                "role": "user"
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
    favorite_genres: List[str] = []
    favorite_authors: List[str] = []
    
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
                "favorite_genres": ["Fantasy"],
                "favorite_authors": ["Andrzej Sapkowski"]
            }
        }


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    favorite_genres: Optional[List[str]] = None
    favorite_authors: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Jan Maria Kowalski",
                "favorite_genres": ["Fantasy", "Horror"],
                "favorite_authors": ["Andrzej Sapkowski", "Stephen King"]
            }
        }
