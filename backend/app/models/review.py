from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId



from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema




class Review(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    book_id: str  # ObjectId as string
    user_id: str  # ObjectId as string
    rating: int = Field(ge=1, le=5)  # Rating from 1 to 5
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_verified: bool = False  # Whether user actually borrowed the book
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "book_id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "rating": 5,
                "comment": "Wspaniała książka! Gorąco polecam wszystkim miłośnikom fantasy.",
                "is_verified": True
            }
        }


class ReviewCreate(BaseModel):
    book_id: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "book_id": "507f1f77bcf86cd799439011",
                "rating": 5,
                "comment": "Fantastyczna lektura!"
            }
        }


class ReviewResponse(BaseModel):
    id: str = Field(alias="_id")
    book_id: str
    user_id: str
    username: Optional[str] = None  # Populated from user data
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    is_verified: bool
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439013",
                "book_id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "username": "jkowalski",
                "rating": 5,
                "comment": "Wspaniała książka!",
                "created_at": "2024-01-15T10:30:00",
                "is_verified": True
            }
        }
