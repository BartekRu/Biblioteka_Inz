"""
Backfill normalized recommendation fields for existing books.

Run from the backend directory:
    python scripts/backfill_book_contract.py
"""

import os
import sys
from pathlib import Path

from pymongo import MongoClient, UpdateOne

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.utils.book_contract import enrich_book_contract  # noqa: E402


MONGO_URI = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "biblioteka")
BATCH_SIZE = 500


def main():
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]

    operations = []
    updated = 0

    for book in db.books.find({}):
        normalized = enrich_book_contract(dict(book))
        update = {
            "authors": normalized.get("authors", []),
            "genres": normalized.get("genres", []),
            "canonical_genres": normalized.get("canonical_genres", []),
            "recommendation_clusters": normalized.get("recommendation_clusters", []),
            "series_key": normalized.get("series_key"),
        }
        operations.append(UpdateOne({"_id": book["_id"]}, {"$set": update}))

        if len(operations) >= BATCH_SIZE:
            result = db.books.bulk_write(operations, ordered=False)
            updated += result.modified_count
            operations = []

    if operations:
        result = db.books.bulk_write(operations, ordered=False)
        updated += result.modified_count

    db.books.create_index("authors")
    db.books.create_index("genres")
    db.books.create_index("canonical_genres")
    db.books.create_index("recommendation_clusters")
    db.books.create_index("series_key")
    db.interactions.create_index([("user_id", 1), ("interaction_type", 1), ("created_at", -1)])
    db.interactions.create_index(
        [("user_id", 1), ("book_id", 1), ("interaction_type", 1), ("created_at", -1)]
    )
    db.loans.create_index([("user_id", 1), ("status", 1)])

    print(f"Backfill complete. Modified {updated} books.")
    client.close()


if __name__ == "__main__":
    main()
