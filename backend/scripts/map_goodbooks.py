import csv
import asyncio
from pprint import pprint
from motor.motor_asyncio import AsyncIOMotorClient
from rapidfuzz import fuzz, process
from unidecode import unidecode



# ==============================================
# CONFIG — DOSTOSUJ DO SWOJEJ BAZY
# ==============================================
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "biblioteka"
COLLECTION = "books"

GOODBOOKS_CSV = "./books.csv"   # <- plik z goodbooks-10k
FUZZY_THRESHOLD = 85            # minimalna zgodność dla fuzzy match
# ==============================================


def normalize(text: str) -> str:
    if not text:
        return ""
    t = unidecode(text).lower().strip()
    return " ".join(t.split())


async def map_books():
    # ----------------------------------------------
    # 1. Wczytaj książki goodbooks-10k
    # ----------------------------------------------
    print("Wczytywanie goodbooks CSV...")

    goodbooks = []   # list of dicts
    goodbooks_by_isbn = {}
    goodbooks_titles = []

    with open(GOODBOOKS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # spodziewane kolumny:
            # book_id, authors, isbn, original_title, title
            book = {
                "book_id": int(row["book_id"]),
                "title": row["title"],
                "authors": row["authors"],
                "isbn": row.get("isbn", ""),
            }
            goodbooks.append(book)

            # indeksy
            if row.get("isbn"):
                goodbooks_by_isbn[row["isbn"]] = book

            norm_title = normalize(f"{row['title']} {row['authors']}")
            goodbooks_titles.append((norm_title, book))

    print(f"Wczytano {len(goodbooks)} książek z goodbooks.")

    # ----------------------------------------------
    # 2. Otwórz MongoDB
    # ----------------------------------------------
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    col = db[COLLECTION]

    books = col.find()
    updates = 0
    no_match = []

    # ----------------------------------------------
    # 3. Przetwarzanie książek z MongoDB
    # ----------------------------------------------
    print("\nRozpoczynam mapowanie książek...")

    async for b in books:
        mongo_id = b["_id"]
        title = b.get("title", "")
        author = b.get("author", "")
        isbn = b.get("isbn") or None

        print("\n-----------------------------------")
        print(f"Mongo książka: {title} — {author} (ISBN={isbn})")

        match = None

        # 3A — próba dopasowania po ISBN
        if isbn and isbn in goodbooks_by_isbn:
            match = goodbooks_by_isbn[isbn]
            print(f"🎯 Dopasowano po ISBN: {isbn} → book_id={match['book_id']}")

        else:
            # 3B — próbuj dopasować po title+author (normalized)
            norm_key = normalize(f"{title} {author}")

            best = process.extractOne(
                norm_key,
                [t for t, _ in goodbooks_titles],
                scorer=fuzz.ratio
            )

            if best and best[1] >= FUZZY_THRESHOLD:
                idx = [t for t, _ in goodbooks_titles].index(best[0])
                match = goodbooks_titles[idx][1]

                print(f"✨ Fuzzy match: confidence={best[1]}% → book_id={match['book_id']}")
            else:
                print("❌ Nie znaleziono dopasowania")
                no_match.append((title, author))
                continue

        # 3C — Zapisz wynik do MongoDB
        if match:
            await col.update_one(
                {"_id": mongo_id},
                {"$set": {"goodbooks_book_id": match["book_id"]}}
            )
            updates += 1
            print(f"💾 Zaktualizowano: {title} → goodbooks_book_id = {match['book_id']}")

    # ----------------------------------------------
    # 4. Raport
    # ----------------------------------------------
    print("\n===================================")
    print(f"Zaktualizowano książek: {updates}")
    print(f"Nie dopasowano: {len(no_match)}")
    if no_match:
        print("\n❌ Lista książek bez dopasowania:")
        pprint(no_match)
    print("===================================")

    client.close()


if __name__ == "__main__":
    asyncio.run(map_books())
