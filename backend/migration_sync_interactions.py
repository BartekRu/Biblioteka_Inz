"""
migration_sync_interactions.py - Skrypt migracyjny (PROSTY)

Jednorazowy skrypt do:
1. Przetworzenia starych recenzji i wypożyczeń
2. Stworzenia brakujących interakcji
3. Wygenerowania embeddingów dla istniejących użytkowników

UŻYCIE:
    python migration_sync_interactions.py
"""

import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe
load_dotenv()

# Wagi dla różnych typów interakcji
INTERACTION_WEIGHTS = {"borrow": 1.0, "review": 0.8, "reserve": 0.6, "view": 0.3}


async def get_db():
    """Połącz się z MongoDB"""
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "biblioteka")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    print(f"📡 Połączono z MongoDB: {mongo_url}/{db_name}")
    return db, client


async def create_interactions_from_reviews(db) -> int:
    """
    Stwórz interakcje typu 'review' dla wszystkich istniejących recenzji
    """
    print("\n📝 Przetwarzanie recenzji...")

    count_created = 0
    count_skipped = 0

    cursor = db.reviews.find({})

    async for review in cursor:
        user_id = str(review["user_id"])
        book_id = str(review["book_id"])
        rating = review.get("rating", 3)
        created_at = review.get("created_at", datetime.utcnow())

        # Sprawdź czy interakcja już istnieje
        existing = await db.interactions.find_one(
            {"user_id": user_id, "book_id": book_id, "interaction_type": "review"}
        )

        if existing:
            count_skipped += 1
            continue

        # Utwórz interakcję
        interaction_doc = {
            "user_id": user_id,
            "book_id": book_id,
            "interaction_type": "review",
            "rating": rating,
            "weight": INTERACTION_WEIGHTS["review"],
            "timestamp": created_at,
            "metadata": {"source": "migration_from_reviews", "migrated_at": datetime.utcnow()},
        }

        await db.interactions.insert_one(interaction_doc)
        count_created += 1

        if count_created % 100 == 0:
            print(f"   Utworzono {count_created} interakcji...")

    print(f"✅ Recenzje: {count_created} utworzonych, {count_skipped} pominiętych")
    return count_created


async def create_interactions_from_loans(db) -> int:
    """
    Stwórz interakcje typu 'borrow' dla wszystkich wypożyczeń
    """
    print("\n📚 Przetwarzanie wypożyczeń...")

    count_created = 0
    count_skipped = 0

    cursor = db.loans.find({})

    async for loan in cursor:
        user_id = str(loan["user_id"])
        book_id = str(loan["book_id"])
        borrowed_at = loan.get("borrowed_at", datetime.utcnow())

        # Sprawdź czy interakcja już istnieje (z tą samą datą)
        existing = await db.interactions.find_one(
            {
                "user_id": user_id,
                "book_id": book_id,
                "interaction_type": "borrow",
                "timestamp": borrowed_at,
            }
        )

        if existing:
            count_skipped += 1
            continue

        # Utwórz interakcję
        interaction_doc = {
            "user_id": user_id,
            "book_id": book_id,
            "interaction_type": "borrow",
            "rating": None,
            "weight": INTERACTION_WEIGHTS["borrow"],
            "timestamp": borrowed_at,
            "metadata": {
                "source": "migration_from_loans",
                "loan_id": str(loan["_id"]),
                "migrated_at": datetime.utcnow(),
            },
        }

        await db.interactions.insert_one(interaction_doc)
        count_created += 1

        if count_created % 100 == 0:
            print(f"   Utworzono {count_created} interakcji...")

    print(f"✅ Wypożyczenia: {count_created} utworzonych, {count_skipped} pominiętych")
    return count_created


async def get_interaction_stats(db) -> dict:
    """Pobierz statystyki interakcji"""
    total = await db.interactions.count_documents({})
    by_type = {}

    for int_type in ["borrow", "review", "view", "reserve"]:
        count = await db.interactions.count_documents({"interaction_type": int_type})
        by_type[int_type] = count

    unique_users = len(await db.interactions.distinct("user_id"))
    unique_books = len(await db.interactions.distinct("book_id"))

    return {
        "total": total,
        "by_type": by_type,
        "unique_users": unique_users,
        "unique_books": unique_books,
    }


async def run_migration():
    """
    Główna funkcja migracji
    """
    print("=" * 70)
    print("🔄 MIGRACJA INTERAKCJI")
    print("=" * 70)

    # Połącz z bazą
    db, client = await get_db()

    try:
        # Krok 1: Statystyki przed migracją
        print("\n📊 Statystyki PRZED migracją:")
        stats_before = await get_interaction_stats(db)
        print(f"   Wszystkie interakcje: {stats_before['total']:,}")
        print(f"   Unikalni użytkownicy: {stats_before['unique_users']:,}")
        print(f"   Unikalne książki: {stats_before['unique_books']:,}")
        for int_type, count in stats_before["by_type"].items():
            if count > 0:
                print(f"   - {int_type}: {count:,}")

        # Krok 2: Stwórz interakcje z recenzji
        reviews_count = await create_interactions_from_reviews(db)

        # Krok 3: Stwórz interakcje z wypożyczeń
        loans_count = await create_interactions_from_loans(db)

        # Krok 4: Statystyki po migracji
        print("\n📊 Statystyki PO migracji:")
        stats_after = await get_interaction_stats(db)
        print(f"   Wszystkie interakcje: {stats_after['total']:,}")
        print(f"   Unikalni użytkownicy: {stats_after['unique_users']:,}")
        print(f"   Unikalne książki: {stats_after['unique_books']:,}")
        for int_type, count in stats_after["by_type"].items():
            if count > 0:
                print(f"   - {int_type}: {count:,}")

        print("\n" + "=" * 70)
        print("✅ MIGRACJA ZAKOŃCZONA")
        print("=" * 70)
        print(f"📊 Podsumowanie:")
        print(f"   - Interakcje z recenzji: {reviews_count:,}")
        print(f"   - Interakcje z wypożyczeń: {loans_count:,}")
        print(f"   - Łącznie nowych: {reviews_count + loans_count:,}")
        print(f"   - Wszystkich interakcji: {stats_after['total']:,}")
        print("\n⚠️  UWAGA: Teraz musisz zrestartować backend!")
        print("   Backend załaduje te interakcje i wygeneruje embeddingi.")
        print("=" * 70)

    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(run_migration())
