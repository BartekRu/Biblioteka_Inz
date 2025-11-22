from pydantic import BaseModel, Field
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


class Book(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    title: str
    author: str
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    genre: List[str] = []
    description: Optional[str] = None
    cover_image: Optional[str] = None
    language: str = "pl"
    pages: Optional[int] = None
    
    # Library-specific fields
    total_copies: int = 1
    available_copies: int = 1
    location: Optional[str] = None  # e.g., "Oddział Mokotów, Regał A5"
    
    # Statistics
    total_loans: int = 0
    total_reviews: int = 0
    average_rating: float = 0.0
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    added_by: Optional[str] = None  # User ID who added the book
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "title": "Wiedźmin: Ostatnie życzenie",
                "author": "Andrzej Sapkowski",
                "isbn": "978-83-7469-470-1",
                "publisher": "SuperNowa",
                "publication_year": 1993,
                "genre": ["Fantasy", "Opowiadania"],
                "description": "Zbiór opowiadań o wiedźminie Geralcie",
                "language": "pl",
                "pages": 332,
                "total_copies": 3,
                "available_copies": 2,
                "location": "Oddział Śródmieście, Regał F3"
            }
        }


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    genre: List[str] = []
    description: Optional[str] = None
    cover_image: Optional[str] = None
    language: str = "pl"
    pages: Optional[int] = None
    total_copies: int = 1
    available_copies: int = 1
    location: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Solaris",
                "author": "Stanisław Lem",
                "isbn": "978-83-7469-795-5",
                "publisher": "Wydawnictwo Literackie",
                "publication_year": 1961,
                "genre": ["Science Fiction", "Filozofia"],
                "description": "Powieść o kontakcie z obcą inteligencją",
                "language": "pl",
                "pages": 224,
                "total_copies": 2,
                "available_copies": 2,
                "location": "Oddział Centrum, Regał SF-12"
            }
        }


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    genre: Optional[List[str]] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    language: Optional[str] = None
    pages: Optional[int] = None
    total_copies: Optional[int] = None
    available_copies: Optional[int] = None
    location: Optional[str] = None


class BookResponse(BaseModel):
    id: str = Field(alias="_id")
    title: str
    author: str
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    genre: List[str] = []
    description: Optional[str] = None
    cover_image: Optional[str] = None
    language: str
    pages: Optional[int] = None
    total_copies: int
    available_copies: int
    location: Optional[str] = None
    total_loans: int
    total_reviews: int
    average_rating: float
    created_at: datetime
    
    class Config:
        populate_by_name = True
