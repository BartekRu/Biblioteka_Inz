from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
from bson import ObjectId


from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema



class Loan(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    book_id: str  # ObjectId as string
    user_id: str  # ObjectId as string
    loan_date: datetime = Field(default_factory=datetime.utcnow)
    due_date: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    return_date: Optional[datetime] = None
    status: str = "active"  # active, returned, overdue
    renewal_count: int = 0
    max_renewals: int = 2
    librarian_notes: Optional[str] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "book_id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "loan_date": "2024-01-01T10:00:00",
                "due_date": "2024-01-31T10:00:00",
                "status": "active",
                "renewal_count": 0
            }
        }


class LoanCreate(BaseModel):
    book_id: str
    user_id: str
    librarian_notes: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "book_id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "librarian_notes": "Nowy wypożyczający"
            }
        }


class LoanResponse(BaseModel):
    id: str = Field(alias="_id")
    book_id: str
    book_title: Optional[str] = None  # Populated from book data
    user_id: str
    username: Optional[str] = None  # Populated from user data
    loan_date: datetime
    due_date: datetime
    return_date: Optional[datetime] = None
    status: str
    renewal_count: int
    max_renewals: int
    is_overdue: bool = False
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439014",
                "book_id": "507f1f77bcf86cd799439011",
                "book_title": "Wiedźmin: Ostatnie życzenie",
                "user_id": "507f1f77bcf86cd799439012",
                "username": "jkowalski",
                "loan_date": "2024-01-01T10:00:00",
                "due_date": "2024-01-31T10:00:00",
                "return_date": None,
                "status": "active",
                "renewal_count": 0,
                "max_renewals": 2,
                "is_overdue": False
            }
        }


class LoanReturn(BaseModel):
    librarian_notes: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "librarian_notes": "Książka w dobrym stanie"
            }
        }
