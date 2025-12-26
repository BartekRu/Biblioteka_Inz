#!/usr/bin/env python3
"""
Populate Database with Test Users and Interactions

Generuje:
- 1000 użytkowników z różnymi profilami czytelniczymi
- 5-20 interakcji (view/borrow/review) na użytkownika
- Realistyczne wzorce oparte na gatunkach
- Różne poziomy aktywności

Użycie:
    python populate_database.py --users 1000 --min-interactions 5 --max-interactions 20

    # Dry run (bez zapisu):
    python populate_database.py --users 100 --dry-run

    # Wyczyść testowe dane:
    python populate_database.py --cleanup
"""

import asyncio
import random
import string
import argparse
from datetime import datetime, timedelta
from typing import List, Dict
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
from dotenv import load_dotenv
from tqdm import tqdm
import bcrypt

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "biblioteka")  # ✅ ZMIENIONE z "library" na "biblioteka"

# ============================================
# PROFIL CZYTELNICZY - RÓŻNE TYPY UŻYTKOWNIKÓW
# ============================================

READER_PROFILES = {
    "fantasy_lover": {
        "name": "Fantasy Lover",
        "preferred_genres": ["Fantasy", "Science Fiction", "Young Adult"],
        "weight": 0.15,  # 15% użytkowników
        "avg_books": 15,
    },
    "romance_reader": {
        "name": "Romance Reader",
        "preferred_genres": ["Romance", "Contemporary", "Historical Fiction"],
        "weight": 0.15,
        "avg_books": 12,
    },
    "mystery_fan": {
        "name": "Mystery Fan",
        "preferred_genres": ["Mystery", "Thriller", "Crime", "Detective"],
        "weight": 0.12,
        "avg_books": 10,
    },
    "classic_reader": {
        "name": "Classic Reader",
        "preferred_genres": ["Classics", "Historical Fiction", "Literary Fiction"],
        "weight": 0.10,
        "avg_books": 8,
    },
    "non_fiction": {
        "name": "Non-Fiction Reader",
        "preferred_genres": ["Non-Fiction", "Biography", "History", "Science"],
        "weight": 0.08,
        "avg_books": 7,
    },
    "ya_enthusiast": {
        "name": "YA Enthusiast",
        "preferred_genres": ["Young Adult", "Fantasy", "Romance", "Dystopian"],
        "weight": 0.12,
        "avg_books": 18,
    },
    "eclectic": {
        "name": "Eclectic Reader",
        "preferred_genres": [],  # Czyta wszystko
        "weight": 0.18,
        "avg_books": 10,
    },
    "casual": {
        "name": "Casual Reader",
        "preferred_genres": [],  # Random
        "weight": 0.10,
        "avg_books": 5,
    },
}


# ============================================
# GENEROWANIE UŻYTKOWNIKÓW
# ============================================


def generate_email(index: int) -> str:
    """Generuje unikalny email"""
    return f"testuser{index:04d}@biblioteka.test"


def generate_password() -> str:
    """Generuje hash hasła dla 'password123'"""
    return bcrypt.hashpw("password123".encode(), bcrypt.gensalt()).decode()


def generate_name(index: int) -> str:
    """Generuje imię i nazwisko"""
    first_names = [
        "Anna",
        "Jan",
        "Maria",
        "Piotr",
        "Katarzyna",
        "Tomasz",
        "Agnieszka",
        "Michał",
        "Magdalena",
        "Krzysztof",
        "Joanna",
        "Andrzej",
        "Ewa",
        "Paweł",
        "Monika",
        "Marcin",
        "Barbara",
        "Łukasz",
        "Aleksandra",
        "Adam",
        "Małgorzata",
        "Robert",
        "Karolina",
        "Jakub",
        "Natalia",
        "Marek",
        "Iwona",
        "Wojciech",
        "Beata",
        "Dariusz",
    ]

    last_names = [
        "Kowalski",
        "Wiśniewski",
        "Wójcik",
        "Kowalczyk",
        "Kamiński",
        "Lewandowski",
        "Zieliński",
        "Szymański",
        "Woźniak",
        "Dąbrowski",
        "Kozłowski",
        "Jankowski",
        "Mazur",
        "Wojciechowski",
        "Kwiatkowski",
        "Krawczyk",
        "Kaczmarek",
        "Piotrowski",
        "Grabowski",
        "Nowakowski",
        "Pawłowski",
        "Michalski",
        "Nowicki",
        "Adamczyk",
    ]

    first = random.choice(first_names)
    last = random.choice(last_names)
    return f"{first} {last}"


def assign_reader_profile() -> str:
    """Przypisz profil czytelniczy na podstawie wag"""
    profiles = list(READER_PROFILES.keys())
    weights = [READER_PROFILES[p]["weight"] for p in profiles]
    return random.choices(profiles, weights=weights)[0]


async def create_users(db, num_users: int, dry_run: bool = False) -> List[Dict]:
    """Tworzy użytkowników z różnymi profilami"""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Generating {num_users} users...")

    users = []
    profile_counts = {p: 0 for p in READER_PROFILES.keys()}

    for i in tqdm(range(num_users), desc="Creating users"):
        profile_type = assign_reader_profile()
        profile_counts[profile_type] += 1

        user = {
            "email": generate_email(i),
            "username": f"testuser{i:04d}",  # ✅ DODANE: username field
            "password": generate_password(),
            "name": generate_name(i),
            "role": "user",
            "createdAt": datetime.now() - timedelta(days=random.randint(1, 365)),
            # Metadata dla testów
            "_test_user": True,
            "_reader_profile": profile_type,
        }

        users.append(user)

    if not dry_run:
        result = await db.users.insert_many(users)
        print(f"✅ Created {len(result.inserted_ids)} users")

        # Dodaj _id do userów
        for user, user_id in zip(users, result.inserted_ids):
            user["_id"] = user_id
    else:
        # W dry run dodaj fake _id
        for user in users:
            user["_id"] = ObjectId()

    # Pokaż statystyki profili
    print("\n📊 Reader Profile Distribution:")
    for profile, count in sorted(profile_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / num_users) * 100
        print(f"   {READER_PROFILES[profile]['name']:20s}: {count:4d} ({pct:5.1f}%)")

    return users


# ============================================
# GENEROWANIE INTERAKCJI
# ============================================


async def get_books_by_genre(db, genres: List[str], limit: int = 100) -> List[Dict]:
    """Pobierz książki z preferowanych gatunków"""
    if not genres:
        # Eclectic/Casual - losowe książki
        return (
            await db.books.find({"available_copies": {"$gt": 0}}).limit(limit).to_list(length=None)
        )

    # Obsłuż zarówno genre (string) jak i genres (array)
    books = (
        await db.books.find(
            {
                "$or": [
                    {"genre": {"$in": genres}},
                    {"genres": {"$in": genres}},
                ],
                "available_copies": {"$gt": 0},
            }
        )
        .limit(limit)
        .to_list(length=None)
    )

    return books


async def create_interactions_for_user(
    db, user: Dict, all_books: List[Dict], min_interactions: int, max_interactions: int
) -> List[Dict]:
    """Generuje realistyczne interakcje dla użytkownika"""
    profile_type = user["_reader_profile"]
    profile = READER_PROFILES[profile_type]

    # Liczba interakcji bazowana na profilu
    base_count = profile["avg_books"]
    num_interactions = random.randint(
        max(min_interactions, base_count - 3), min(max_interactions, base_count + 5)
    )

    # Pobierz książki z preferowanych gatunków
    preferred_genres = profile["preferred_genres"]
    if preferred_genres:
        genre_books = [
            b
            for b in all_books
            if any(g in b.get("genres", []) or g == b.get("genre") for g in preferred_genres)
        ]

        # 70% z preferowanych gatunków, 30% random
        num_preferred = int(num_interactions * 0.7)
        num_random = num_interactions - num_preferred

        selected_books = random.sample(
            genre_books if genre_books else all_books,
            min(num_preferred, len(genre_books) if genre_books else len(all_books)),
        )

        if num_random > 0:
            random_books = random.sample(
                [b for b in all_books if b not in selected_books],
                min(num_random, len(all_books) - len(selected_books)),
            )
            selected_books.extend(random_books)
    else:
        # Eclectic/Casual - całkowicie losowe
        selected_books = random.sample(all_books, min(num_interactions, len(all_books)))

    # Generuj interakcje
    interactions = []
    user_created = user["createdAt"]

    for i, book in enumerate(selected_books):
        # Timestamp rosnąco od daty utworzenia konta
        days_offset = random.randint(i * 2, i * 7 + 30)
        timestamp = user_created + timedelta(days=days_offset)

        # 60% borrow, 30% view, 10% review
        interaction_type = random.choices(["borrow", "view", "review"], weights=[0.6, 0.3, 0.1])[0]

        interaction = {
            "user_id": str(user["_id"]),
            "book_id": str(book["_id"]),
            "interaction_type": interaction_type,
            "timestamp": timestamp,
            "metadata": {
                "source": "test_data_generation",
                "_test_interaction": True,
            },
        }

        # Dodaj goodbooks_book_id jeśli istnieje
        if book.get("goodbooks_book_id"):
            interaction["metadata"]["goodbooks_book_id"] = int(book["goodbooks_book_id"])

        # Dla review dodaj rating
        if interaction_type == "review":
            # Wyższe oceny dla preferowanych gatunków
            is_preferred = (
                any(g in book.get("genres", []) or g == book.get("genre") for g in preferred_genres)
                if preferred_genres
                else False
            )

            if is_preferred:
                rating = random.choices([3, 4, 5], weights=[0.1, 0.3, 0.6])[0]
            else:
                rating = random.choices([2, 3, 4, 5], weights=[0.1, 0.3, 0.4, 0.2])[0]

            interaction["metadata"]["rating"] = rating

        interactions.append(interaction)

    return interactions


async def create_all_interactions(
    db, users: List[Dict], min_interactions: int, max_interactions: int, dry_run: bool = False
) -> int:
    """Generuje interakcje dla wszystkich użytkowników"""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Generating interactions...")

    # Pobierz wszystkie dostępne książki
    all_books = await db.books.find({"available_copies": {"$gt": 0}}).to_list(length=None)
    print(f"📚 Found {len(all_books)} available books")

    if len(all_books) < 10:
        print("❌ Not enough books in database! Need at least 10 books.")
        return 0

    all_interactions = []

    for user in tqdm(users, desc="Creating interactions"):
        interactions = await create_interactions_for_user(
            db, user, all_books, min_interactions, max_interactions
        )
        all_interactions.extend(interactions)

    if not dry_run and all_interactions:
        # Insert w batch'ach po 1000
        batch_size = 1000
        for i in range(0, len(all_interactions), batch_size):
            batch = all_interactions[i : i + batch_size]
            await db.interactions.insert_many(batch)

        print(f"✅ Created {len(all_interactions)} interactions")
    else:
        print(f"{'[DRY RUN] ' if dry_run else ''}Would create {len(all_interactions)} interactions")

    return len(all_interactions)


# ============================================
# CLEANUP
# ============================================


async def cleanup_test_data(db):
    """Usuwa wszystkie testowe dane"""
    print("\n🧹 Cleaning up test data...")

    # Usuń testowych użytkowników
    users_result = await db.users.delete_many({"_test_user": True})
    print(f"   Deleted {users_result.deleted_count} test users")

    # Usuń testowe interakcje
    interactions_result = await db.interactions.delete_many({"metadata._test_interaction": True})
    print(f"   Deleted {interactions_result.deleted_count} test interactions")

    print("✅ Cleanup complete!")


# ============================================
# STATYSTYKI
# ============================================


async def show_statistics(db):
    """Pokaż statystyki bazy"""
    print("\n📊 Database Statistics:")

    # Użytkownicy
    total_users = await db.users.count_documents({})
    test_users = await db.users.count_documents({"_test_user": True})
    print(f"\n👥 Users:")
    print(f"   Total: {total_users}")
    print(f"   Test:  {test_users}")
    print(f"   Real:  {total_users - test_users}")

    # Interakcje
    total_interactions = await db.interactions.count_documents({})
    test_interactions = await db.interactions.count_documents({"metadata._test_interaction": True})
    print(f"\n🔄 Interactions:")
    print(f"   Total: {total_interactions}")
    print(f"   Test:  {test_interactions}")
    print(f"   Real:  {total_interactions - test_interactions}")

    # Breakdown interakcji
    for itype in ["view", "borrow", "review"]:
        count = await db.interactions.count_documents(
            {"interaction_type": itype, "metadata._test_interaction": True}
        )
        print(f"   - {itype}: {count}")

    # Książki
    total_books = await db.books.count_documents({})
    available_books = await db.books.count_documents({"available_copies": {"$gt": 0}})
    print(f"\n📚 Books:")
    print(f"   Total:     {total_books}")
    print(f"   Available: {available_books}")


# ============================================
# MAIN
# ============================================


async def main():
    parser = argparse.ArgumentParser(description="Populate database with test data")
    parser.add_argument("--users", type=int, default=1000, help="Number of users to create")
    parser.add_argument("--min-interactions", type=int, default=5, help="Min interactions per user")
    parser.add_argument(
        "--max-interactions", type=int, default=20, help="Max interactions per user"
    )
    parser.add_argument("--dry-run", action="store_true", help="Don't actually write to database")
    parser.add_argument("--cleanup", action="store_true", help="Remove all test data")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")

    args = parser.parse_args()

    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]

    print("=" * 60)
    print("📚 Library Database Populator")
    print("=" * 60)

    try:
        if args.cleanup:
            # Cleanup mode
            confirm = input("\n⚠️  This will delete ALL test data. Continue? (yes/no): ")
            if confirm.lower() == "yes":
                await cleanup_test_data(db)
                await show_statistics(db)
            else:
                print("Cancelled.")
            return

        if args.stats:
            # Stats only
            await show_statistics(db)
            return

        # Normal mode - populate
        print(f"\nConfiguration:")
        print(f"   Users: {args.users}")
        print(f"   Interactions per user: {args.min_interactions}-{args.max_interactions}")
        print(f"   Dry run: {args.dry_run}")

        if not args.dry_run:
            confirm = input("\n⚠️  This will add data to your database. Continue? (yes/no): ")
            if confirm.lower() != "yes":
                print("Cancelled.")
                return

        # Create users
        users = await create_users(db, args.users, args.dry_run)

        # Create interactions
        total_interactions = await create_all_interactions(
            db, users, args.min_interactions, args.max_interactions, args.dry_run
        )

        # Show final statistics
        if not args.dry_run:
            await show_statistics(db)

        print("\n" + "=" * 60)
        print("✅ Population complete!")
        print("=" * 60)

        if not args.dry_run:
            print("\n💡 To remove test data later, run:")
            print("   python populate_database.py --cleanup")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
