"""
Skrypt do importu książek z goodbooks-10k do MongoDB.

Uruchom:
    cd backend
    python scripts/import_goodbooks.py

Wymaga:
    pip install pandas pymongo requests
"""

import pandas as pd
import requests
from pymongo import MongoClient
from datetime import datetime
import os
from io import StringIO

MONGO_URI = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "biblioteka")

BOOKS_URL = "https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/books.csv"
TAGS_URL = "https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/tags.csv"
BOOK_TAGS_URL = "https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/book_tags.csv"


def download_csv(url: str) -> pd.DataFrame:
    """Pobierz CSV z URL"""
    print(f"📥 Pobieranie: {url.split('/')[-1]}...")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))


def get_genres_for_books(book_tags_df: pd.DataFrame, tags_df: pd.DataFrame) -> dict:
    """
    Stwórz mapowanie book_id -> lista gatunków (tagów).
    Wybieramy top 5 tagów dla każdej książki.
    """
    print("🏷️  Przetwarzanie tagów...")
    
    genre_keywords = [
        'fiction', 'fantasy', 'romance', 'mystery', 'thriller', 'horror',
        'science-fiction', 'sci-fi', 'historical', 'biography', 'non-fiction',
        'nonfiction', 'young-adult', 'ya', 'children', 'classics', 'classic',
        'adventure', 'comedy', 'humor', 'drama', 'poetry', 'crime', 'war',
        'philosophy', 'psychology', 'self-help', 'history', 'politics',
        'science', 'travel', 'cooking', 'art', 'music', 'sports', 'business',
        'economics', 'religion', 'spirituality', 'paranormal', 'dystopia',
        'utopia', 'magic', 'vampires', 'werewolves', 'zombies', 'apocalyptic',
        'contemporary', 'literary', 'graphic-novel', 'manga', 'comic'
    ]
    
    tag_names = dict(zip(tags_df['tag_id'], tags_df['tag_name']))
    
    book_genres = {}
    
    for goodreads_book_id, group in book_tags_df.groupby('goodreads_book_id'):
        top_tags = group.nlargest(10, 'count')
        
        genres = []
        for _, row in top_tags.iterrows():
            tag_name = tag_names.get(row['tag_id'], '').lower()
            
            for keyword in genre_keywords:
                if keyword in tag_name:
                    clean_name = tag_name.replace('-', ' ').title()
                    if clean_name not in genres:
                        genres.append(clean_name)
                    break
            
            if len(genres) >= 3: 
                break
        
        if genres:
            book_genres[goodreads_book_id] = genres
    
    return book_genres


def transform_book(row: pd.Series, book_genres: dict) -> dict:
    """Przekształć wiersz CSV na dokument MongoDB"""
    
    goodbooks_id = int(row['book_id'])
    goodreads_id = int(row['goodreads_book_id']) if pd.notna(row.get('goodreads_book_id')) else None
    
    genres = book_genres.get(goodreads_id, [])
    if not genres:
        genres = book_genres.get(goodbooks_id, ["Fiction"])  
    
    pub_year = None
    if pd.notna(row.get('original_publication_year')):
        try:
            pub_year = int(row['original_publication_year'])
        except (ValueError, TypeError):
            pass
    
    authors = str(row.get('authors', 'Unknown'))
    primary_author = authors.split(',')[0].strip()
    
    return {
        "title": str(row['title']),
        "author": primary_author,
        "authors_full": authors,
        "isbn": str(row['isbn']) if pd.notna(row.get('isbn')) else None,
        "isbn13": str(row['isbn13']) if pd.notna(row.get('isbn13')) else None,
        "publication_year": pub_year,
        "publisher": None, 
        "genre": genres,
        "language": "en",  
        "pages": None, 
        "description": None, 
        
        "average_rating": float(row['average_rating']) if pd.notna(row.get('average_rating')) else 0.0,
        "ratings_count": int(row['ratings_count']) if pd.notna(row.get('ratings_count')) else 0,
        "reviews_count": int(row['work_text_reviews_count']) if pd.notna(row.get('work_text_reviews_count')) else 0,
        
        "image_url": str(row['image_url']) if pd.notna(row.get('image_url')) else None,
        "small_image_url": str(row['small_image_url']) if pd.notna(row.get('small_image_url')) else None,
        
        "goodbooks_book_id": goodbooks_id,
        "goodreads_book_id": goodreads_id,
        
        "total_copies": 3,
        "available_copies": 3,
        "location": "Magazyn główny",
        "total_loans": 0,
        
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


def main():
    print("=" * 60)
    print("📚 Import książek z goodbooks-10k do MongoDB")
    print("=" * 60)
    
    print(f"\n🔌 Łączenie z MongoDB: {MONGO_URI}")
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    books_collection = db.books
    
    print("\n📥 Pobieranie danych z GitHub...")
    books_df = download_csv(BOOKS_URL)
    print(f"   ✓ books.csv: {len(books_df)} książek")
    
    tags_df = download_csv(TAGS_URL)
    print(f"   ✓ tags.csv: {len(tags_df)} tagów")
    
    book_tags_df = download_csv(BOOK_TAGS_URL)
    print(f"   ✓ book_tags.csv: {len(book_tags_df)} powiązań")
    
    book_genres = get_genres_for_books(book_tags_df, tags_df)
    print(f"   ✓ Gatunki dla {len(book_genres)} książek")
    
    existing_ids = set()
    for doc in books_collection.find({"goodbooks_book_id": {"$exists": True}}, {"goodbooks_book_id": 1}):
        existing_ids.add(doc.get("goodbooks_book_id"))
    print(f"\n📊 Istniejące książki z goodbooks_book_id: {len(existing_ids)}")
    
    print("\n🔄 Przekształcanie danych...")
    documents = []
    skipped = 0
    
    for _, row in books_df.iterrows():
        book_id = int(row['book_id'])
        
        if book_id in existing_ids:
            skipped += 1
            continue
        
        doc = transform_book(row, book_genres)
        documents.append(doc)
    
    print(f"   ✓ Przygotowano: {len(documents)} nowych książek")
    print(f"   ⏭️  Pominięto (duplikaty): {skipped}")
    
    if documents:
        print(f"\n💾 Importowanie do MongoDB...")
        
        batch_size = 500
        total_inserted = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            result = books_collection.insert_many(batch)
            total_inserted += len(result.inserted_ids)
            print(f"   ✓ Wstawiono: {total_inserted}/{len(documents)}")
        
        print(f"\n✅ Import zakończony! Dodano {total_inserted} książek.")
    else:
        print("\n⚠️  Brak nowych książek do importu.")
    
    total_books = books_collection.count_documents({})
    print(f"\n📈 Łączna liczba książek w bazie: {total_books}")
    
    print("\n🔍 Tworzenie indeksów...")
    books_collection.create_index("goodbooks_book_id", unique=True, sparse=True)
    books_collection.create_index("title")
    books_collection.create_index("author")
    books_collection.create_index("genre")
    books_collection.create_index("average_rating")
    books_collection.create_index([("title", "text"), ("author", "text")])
    print("   ✓ Indeksy utworzone")
    
    print("\n" + "=" * 60)
    print("🎉 Gotowe!")
    print("=" * 60)


if __name__ == "__main__":
    main()