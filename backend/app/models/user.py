from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId


class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v, info=None):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str) and ObjectId.is_valid(v):
            return v
        raise ValueError("Invalid ObjectId")


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "user"  


class UserCreate(UserBase):
    username: str
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    favorite_genres: Optional[List[str]] = None
    favorite_authors: Optional[List[str]] = None
    goodbooks_user_id: Optional[int] = None


class UserPreferences(BaseModel):
    favorite_genres: Optional[List[str]] = None
    favorite_authors: Optional[List[str]] = None
    disliked_genres: Optional[List[str]] = None


class UserInDB(UserBase):
    id: str = Field(alias="_id")
    username: Optional[str] = None
    hashed_password: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    favorite_genres: Optional[List[str]] = None
    favorite_authors: Optional[List[str]] = None
    
    goodbooks_user_id: Optional[int] = None
    
    preferences: Optional[UserPreferences] = None
    
    borrowed_books: Optional[List[str]] = None
    reading_history: Optional[List[str]] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class UserResponse(BaseModel):
    id: str = Field(alias="_id")
    email: EmailStr
    username: Optional[str] = None
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    goodbooks_user_id: Optional[int] = None
    favorite_genres: Optional[List[str]] = None     
    favorite_authors: Optional[List[str]] = None
    preferences: Optional[UserPreferences] = None
    
    class Config:
        populate_by_name = True


class User(UserBase):
    """Model dla nowego użytkownika (bez ID)"""
    pass