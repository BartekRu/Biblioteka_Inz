"""
Skrypt inicjalizujący bazę danych z przykładowymi danymi
Uruchom: python init_db.py
"""

import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.utils.security import get_password_hash

# Sample books data
SAMPLE_BOOKS = [
    {
        "title": "Wiedźmin: Ostatnie życzenie",
        "author": "Andrzej Sapkowski",
        "isbn": "978-83-7469-470-1",
        "publisher": "SuperNowa",
        "publication_year": 1993,
        "genre": ["Fantasy", "Opowiadania"],
        "description": "Zbiór opowiadań o wiedźminie Geralcie z Rivii, który podróżuje po fantastycznym świecie, zabijając potwory i rozwiązując problemy ludzi.",
        "language": "pl",
        "pages": 332,
        "total_copies": 3,
        "available_copies": 3,
        "location": "Oddział Śródmieście, Regał F3",
        "total_loans": 0,
        "total_reviews": 0,
        "average_rating": 0.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "title": "Solaris",
        "author": "Stanisław Lem",
        "isbn": "978-83-7469-795-5",
        "publisher": "Wydawnictwo Literackie",
        "publication_year": 1961,
        "genre": ["Science Fiction", "Filozofia"],
        "description": "Powieść o kontakcie z obcą inteligencją na planecie Solaris, która zmusza ludzi do konfrontacji z własnymi lękami i wspomnieniami.",
        "language": "pl",
        "pages": 224,
        "total_copies": 2,
        "available_copies": 2,
        "location": "Oddział Centrum, Regał SF-12",
        "total_loans": 0,
        "total_reviews": 0,
        "average_rating": 0.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "title": "Pan Tadeusz",
        "author": "Adam Mickiewicz",
        "isbn": "978-83-240-0000-1",
        "publisher": "Greg",
        "publication_year": 1834,
        "genre": ["Epopeja", "Klasyka"],
        "description": "Ostatni wielki epos kultury szlacheckiej, opowiadający o życiu szlachty polskiej na Litwie na początku XIX wieku.",
        "language": "pl",
        "pages": 256,
        "total_copies": 5,
        "available_copies": 5,
        "location": "Oddział Mokotów, Regał KL-5",
        "total_loans": 0,
        "total_reviews": 0,
        "average_rating": 0.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "title": "Zbrodnia i kara",
        "author": "Fiodor Dostojewski",
        "isbn": "978-83-240-3456-7",
        "publisher": "Świat Książki",
        "publication_year": 1866,
        "genre": ["Powieść psychologiczna", "Klasyka"],
        "description": "Historia studenta Raskolnikowa, który popełnia morderstwo i zmaga się z konsekwencjami swojego czynu.",
        "language": "pl",
        "pages": 656,
        "total_copies": 4,
        "available_copies": 4,
        "location": "Oddział Ursynów, Regał KL-8",
        "total_loans": 0,
        "total_reviews": 0,
        "average_rating": 0.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "title": "Quo Vadis",
        "author": "Henryk Sienkiewicz",
        "isbn": "978-83-240-1234-5",
        "publisher": "Greg",
        "publication_year": 1896,
        "genre": ["Powieść historyczna", "Klasyka"],
        "description": "Powieść historyczna osadzona w czasach Nerona, opowiadająca o miłości rzymskiego patrycjusza do chrześcijanki.",
        "language": "pl",
        "pages": 608,
        "total_copies": 3,
        "available_copies": 3,
        "location": "Oddział Żoliborz, Regał KL-3",
        "total_loans": 0,
        "total_reviews": 0,
        "average_rating": 0.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "title": "1984",
        "author": "George Orwell",
        "isbn": "978-83-240-5678-9",
        "publisher": "Muza",
        "publication_year": 1949,
        "genre": ["Dystopia", "Science Fiction"],
        "description": "Dystopia o totalitarnym państwie Oceanii, gdzie Wielki Brat obserwuje każdego obywatela.",
        "language": "pl",
        "pages": 328,
        "total_copies": 4,
        "available_copies": 4,
        "location": "Oddział Praga, Regał SF-5",
        "total_loans": 0,
        "total_reviews": 0,
        "average_rating": 0.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "title": "Władca Pierścieni: Drużyna Pierścienia",
        "author": "J.R.R. Tolkien",
        "isbn": "978-83-7469-123-6",
        "publisher": "Amber",
        "publication_year": 1954,
        "genre": ["Fantasy", "Przygodowa"],
        "description": "Pierwsza część epickiej trylogii o podróży hobbita Froda w celu zniszczenia Jedynego Pierścienia.",
        "language": "pl",
        "pages": 544,
        "total_copies": 5,
        "available_copies": 5,
        "location": "Oddział Wola, Regał F-1",
        "total_loans": 0,
        "total_reviews": 0,
        "average_rating": 0.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "title": "Mistrz i Małgorzata",
        "author": "Michaił Bułhakow",
        "isbn": "978-83-240-7890-1",
        "publisher": "Muza",
        "publication_year": 1967,
        "genre": ["Fantastyka", "Satyra"],
        "description": "Satyryczna powieść o wizycie diabła w Moskwie lat 30. XX wieku, przeplatana historią Piłata i Jezusa.",
        "language": "pl",
        "pages": 464,
        "total_copies": 3,
        "available_copies": 3,
        "location": "Oddział Ochota, Regał KL-12",
        "total_loans": 0,
        "total_reviews": 0,
        "average_rating": 0.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "title": "Harry Potter i Kamień Filozoficzny",
        "author": "J.K. Rowling",
        "isbn": "978-83-7469-234-9",
        "publisher": "Media Rodzina",
        "publication_year": 1997,
        "genre": ["Fantasy", "Dla młodzieży"],
        "description": "Pierwsza część przygód Harry'ego Pottera, który odkrywa, że jest czarodziejem i rozpoczyna naukę w Hogwarcie.",
        "language": "pl",
        "pages": 328,
        "total_copies": 6,
        "available_copies": 6,
        "location": "Oddział Bielany, Regał DM-2",
        "total_loans": 0,
        "total_reviews": 0,
        "average_rating": 0.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "title": "Mały Książę",
        "author": "Antoine de Saint-Exupéry",
        "isbn": "978-83-240-9012-5",
        "publisher": "Znak",
        "publication_year": 1943,
        "genre": ["Bajka filozoficzna", "Dla dzieci"],
        "description": "Filozoficzna opowieść o małym chłopcu z asteroidy, który podróżuje po planetach i poznaje różne osoby.",
        "language": "pl",
        "pages": 96,
        "total_copies": 4,
        "available_copies": 4,
        "location": "Oddział Targówek, Regał DD-1",
        "total_loans": 0,
        "total_reviews": 0,
        "average_rating": 0.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
]


async def init_database():
    """Initialize database with sample data"""
    print("🚀 Inicjalizacja bazy danych...")
    
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        print("🗑️  Usuwanie istniejących kolekcji...")
        await db.users.drop()
        await db.books.drop()
        await db.reviews.drop()
        await db.loans.drop()
        
        # Create indexes
        print("📇 Tworzenie indeksów...")
        
        # Users indexes
        await db.users.create_index([("email", ASCENDING)], unique=True)
        await db.users.create_index([("username", ASCENDING)], unique=True)
        
        # Books indexes
        await db.books.create_index([("title", ASCENDING)])
        await db.books.create_index([("author", ASCENDING)])
        await db.books.create_index([("genre", ASCENDING)])
        await db.books.create_index([("isbn", ASCENDING)], unique=True, sparse=True)
        
        # Reviews indexes
        await db.reviews.create_index([("book_id", ASCENDING)])
        await db.reviews.create_index([("user_id", ASCENDING)])
        await db.reviews.create_index([("created_at", DESCENDING)])
        
        # Loans indexes
        await db.loans.create_index([("book_id", ASCENDING)])
        await db.loans.create_index([("user_id", ASCENDING)])
        await db.loans.create_index([("status", ASCENDING)])
        await db.loans.create_index([("due_date", ASCENDING)])
        
        # Insert sample admin user
        print("👤 Tworzenie użytkownika administratora...")
        admin_user = {
            "email": "admin@biblioteka.pl",
            "username": "admin",
            "hashed_password": get_password_hash("admin123"),
            "full_name": "Administrator Systemu",
            "role": "admin",
            "is_active": True,
            "favorite_genres": [],
            "favorite_authors": [],
            "reading_history": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db.users.insert_one(admin_user)
        
        # Insert sample librarian user
        print("👤 Tworzenie użytkownika bibliotekarza...")
        librarian_user = {
            "email": "bibliotekarz@biblioteka.pl",
            "username": "bibliotekarz",
            "hashed_password": get_password_hash("bibliotekarz123"),
            "full_name": "Jan Kowalski",
            "role": "librarian",
            "is_active": True,
            "favorite_genres": [],
            "favorite_authors": [],
            "reading_history": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db.users.insert_one(librarian_user)
        
        # Insert sample regular user
        print("👤 Tworzenie przykładowego użytkownika...")
        regular_user = {
            "email": "uzytkownik@example.com",
            "username": "uzytkownik",
            "hashed_password": get_password_hash("uzytkownik123"),
            "full_name": "Anna Nowak",
            "role": "user",
            "is_active": True,
            "favorite_genres": ["Fantasy", "Science Fiction"],
            "favorite_authors": ["Andrzej Sapkowski", "Stanisław Lem"],
            "reading_history": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db.users.insert_one(regular_user)
        
        # Insert sample books
        print(f"📚 Dodawanie {len(SAMPLE_BOOKS)} przykładowych książek...")
        await db.books.insert_many(SAMPLE_BOOKS)
        
        print("\n✅ Baza danych została pomyślnie zainicjalizowana!")
        print("\n📋 Dane logowania:")
        print("   Administrator:")
        print("   - Login: admin")
        print("   - Hasło: admin123")
        print("\n   Bibliotekarz:")
        print("   - Login: bibliotekarz")
        print("   - Hasło: bibliotekarz123")
        print("\n   Użytkownik:")
        print("   - Login: uzytkownik")
        print("   - Hasło: uzytkownik123")
        print("\n📚 Dodano książek:", len(SAMPLE_BOOKS))
        
    except Exception as e:
        print(f"\n❌ Błąd podczas inicjalizacji: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(init_database())
