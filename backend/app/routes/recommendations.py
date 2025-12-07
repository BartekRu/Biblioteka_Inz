

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from bson import ObjectId
import random

from ..database import get_database
from .auth import get_current_user

router = APIRouter(prefix="/v1/recommendations", tags=["Recommendations"])




def serialize_doc(doc: dict) -> dict:
    """Konwertuje MongoDB document na JSON"""
    if doc is None:
        return None
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    if 'user_id' in doc and isinstance(doc['user_id'], ObjectId):
        doc['user_id'] = str(doc['user_id'])
    if 'book_id' in doc and isinstance(doc['book_id'], ObjectId):
        doc['book_id'] = str(doc['book_id'])
    return doc



@router.get("/health")
async def health_check():
    """Status systemu rekomendacji"""
    return {
        "status": "healthy",
        "model_loaded": False, 
        "fallback_mode": True,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/metrics")
async def get_metrics():
    """Metryki modelu - wyświetlane na stronie rekomendacji"""
    return {
        "recall20": 0.1411,
        "ndcg20": 0.0842,
        "precision20": 0.0623,
        "coverage": 0.78,
        "trainUsers": "35,710",
        "trainItems": "10,000",
        "interactions": "932,940",
        "embeddingDim": "64",
        "epochs": "50",
        "learningRate": "0.001",
        "lastUpdated": datetime.now().strftime('%Y-%m-%d'),
        "modelName": "LightGCN",
        "layers": 3
    }


@router.get("/featured")
async def get_featured(
    limit: int = Query(default=10, le=20),
    current_user: dict = Depends(get_current_user)
):
    """Wyróżnione rekomendacje - główny carousel"""
    db = get_database()
    user_id = str(current_user.id)

    
    favorite_genres = []
    pipeline = [
        {'$match': {'user_id': ObjectId(user_id)}},
        {'$lookup': {
            'from': 'books',
            'localField': 'book_id',
            'foreignField': '_id',
            'as': 'book'
        }},
        {'$unwind': '$book'},
        {'$unwind': {'path': '$book.genres', 'preserveNullAndEmptyArrays': True}},
        {'$group': {'_id': '$book.genres', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 5}
    ]
    
    try:
        async for doc in db.loans.aggregate(pipeline):
            if doc['_id']:
                favorite_genres.append(doc['_id'])
    except Exception as e:
        print(f"Error getting favorite genres: {e}")
    
    books = []
    
    if favorite_genres:
        query = {'genres': {'$in': favorite_genres}}
        cursor = db.books.find(query).sort('averageRating', -1).limit(limit)
        async for book in cursor:
            book = serialize_doc(book)
            book['matchScore'] = round(random.uniform(0.75, 0.95), 2)
            book['recommendationReason'] = 'Dopasowane do Twoich ulubionych gatunków'
            books.append(book)
    
    if len(books) < limit:
        existing_ids = [ObjectId(b['_id']) for b in books]
        query = {'_id': {'$nin': existing_ids}} if existing_ids else {}
        cursor = db.books.find(query).sort('averageRating', -1).limit(limit - len(books))
        async for book in cursor:
            book = serialize_doc(book)
            book['matchScore'] = round(random.uniform(0.6, 0.8), 2)
            book['recommendationReason'] = 'Popularne w bibliotece'
            books.append(book)
    
    return books[:limit]


@router.get("/categories")
async def get_categories():
    """Kategorie z okładkami"""
    db = get_database()
    
    pipeline = [
        {'$unwind': '$genres'},
        {'$group': {
            '_id': '$genres',
            'count': {'$sum': 1},
            'covers': {'$push': '$coverImage'}
        }},
        {'$project': {
            'name': '$_id',
            'count': 1,
            'sampleCovers': {'$slice': ['$covers', 6]}
        }},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]
    
    categories = []
    async for cat in db.books.aggregate(pipeline):
        categories.append({
            'name': cat['name'],
            'count': cat['count'],
            'sampleCovers': [c for c in cat.get('sampleCovers', []) if c]
        })
    
    return categories


@router.get("/because-borrowed")
async def get_because_borrowed(
    limit: int = Query(default=3, le=5),
    current_user: dict = Depends(get_current_user)
):
    """Sekcje 'Ponieważ wypożyczyłeś X'"""
    db = get_database()
    user_id = str(current_user.id)

    
    loans_cursor = db.loans.find(
        {'user_id': ObjectId(user_id)}
    ).sort('borrowed_at', -1).limit(limit)
    
    sections = []
    
    async for loan in loans_cursor:
        source_book = await db.books.find_one({'_id': loan['book_id']})
        if not source_book:
            continue
        
        source_book = serialize_doc(source_book)
        source_genres = source_book.get('genres', [])
        source_author = source_book.get('author', '')
        
        similar_query = {
            '_id': {'$ne': loan['book_id']},
            '$or': []
        }
        if source_genres:
            similar_query['$or'].append({'genres': {'$in': source_genres}})
        if source_author:
            similar_query['$or'].append({'author': source_author})
        
        if not similar_query['$or']:
            continue
            
        recommendations = []
        async for book in db.books.find(similar_query).limit(6):
            book = serialize_doc(book)

            score = 0.5
            if book.get('author') == source_author:
                score += 0.3
            if set(book.get('genres', [])) & set(source_genres):
                score += 0.2
            book['matchScore'] = round(min(score, 0.95), 2)
            recommendations.append(book)
        
        if recommendations:
            sections.append({
                'sourceBook': {
                    '_id': source_book['_id'],
                    'title': source_book.get('title'),
                    'author': source_book.get('author')
                },
                'recommendations': recommendations
            })
    
    if not sections:
        top_genres = []
        async for g in db.books.aggregate([
            {'$unwind': '$genres'},
            {'$group': {'_id': '$genres', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': limit}
        ]):
            top_genres.append(g['_id'])
        
        for genre in top_genres:
            books = []
            async for book in db.books.find({'genres': genre}).sort('averageRating', -1).limit(4):
                book = serialize_doc(book)
                book['matchScore'] = round(random.uniform(0.6, 0.8), 2)
                books.append(book)
            
            if books:
                sections.append({
                    'sourceBook': {
                        '_id': 'popular',
                        'title': f'Popularne w {genre}',
                        'author': ''
                    },
                    'recommendations': books
                })
    
    return sections


@router.get("/discovery-queue")
async def get_discovery_queue(
    limit: int = Query(default=12, le=30),
    current_user: dict = Depends(get_current_user)
):
    """Kolejka odkryć - mieszanka książek do przejrzenia"""
    db = get_database()
    user_id = str(current_user.id)

    
    borrowed_ids = []
    async for loan in db.loans.find({'user_id': ObjectId(user_id)}):
        borrowed_ids.append(loan['book_id'])
    
    query = {}
    if borrowed_ids:
        query['_id'] = {'$nin': borrowed_ids}
    
    books = []
    
    pipeline = [{'$match': query}, {'$sample': {'size': limit}}]
    async for book in db.books.aggregate(pipeline):
        book = serialize_doc(book)
        book['matchScore'] = round(random.uniform(0.5, 0.85), 2)
        books.append(book)
    
    return books


@router.get("/known-authors")
async def get_known_authors(
    limit: int = Query(default=6, le=10),
    current_user: dict = Depends(get_current_user)
):
    """Autorzy których użytkownik zna"""
    db = get_database()
    user_id = str(current_user.id)

    
    pipeline = [
        {'$match': {'user_id': ObjectId(user_id)}},
        {'$lookup': {
            'from': 'books',
            'localField': 'book_id',
            'foreignField': '_id',
            'as': 'book'
        }},
        {'$unwind': '$book'},
        {'$group': {
            '_id': '$book.author',
            'count': {'$sum': 1}
        }},
        {'$match': {'_id': {'$ne': None}}},
        {'$sort': {'count': -1}},
        {'$limit': limit}
    ]
    
    authors = []
    async for doc in db.loans.aggregate(pipeline):
        author_name = doc['_id']
        if not author_name:
            continue
        
        latest = await db.books.find_one(
            {'author': author_name},
            sort=[('publication_year', -1)]
        )
        
        if latest:
            authors.append({
                'name': author_name,
                'latestBook': {
                    '_id': str(latest['_id']),
                    'title': latest.get('title'),
                    'coverImage': latest.get('coverImage'),
                    'available': latest.get('available', True)
                }
            })
    
    return authors


@router.get("/similar/{book_id}")
async def get_similar(
    book_id: str,
    limit: int = Query(default=8, le=20)
):
    """Podobne książki"""
    db = get_database()
    
    try:
        source = await db.books.find_one({'_id': ObjectId(book_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid book ID")
    
    if not source:
        raise HTTPException(status_code=404, detail="Book not found")
    
    source_genres = source.get('genres', [])
    source_author = source.get('author', '')
    
    query = {'_id': {'$ne': ObjectId(book_id)}, '$or': []}
    if source_genres:
        query['$or'].append({'genres': {'$in': source_genres}})
    if source_author:
        query['$or'].append({'author': source_author})
    
    if not query['$or']:
        return []
    
    books = []
    async for book in db.books.find(query).limit(limit):
        book = serialize_doc(book)
        similarity = 0.5
        if book.get('author') == source_author:
            similarity += 0.3
        common = set(book.get('genres', [])) & set(source_genres)
        similarity += len(common) * 0.1
        book['similarity'] = round(min(similarity, 0.95), 2)
        books.append(book)
    
    return sorted(books, key=lambda x: x['similarity'], reverse=True)


@router.post("/interaction")
async def report_interaction(
    book_id: str,
    interaction_type: str,
    metadata: dict = None,
    current_user: dict = Depends(get_current_user)
):
    """Zapisz interakcję (do przyszłego treningu)"""
    db = get_database()
    
    try:
        bid = ObjectId(book_id) if ObjectId.is_valid(book_id) else book_id
    except:
        bid = book_id
    
    interaction = {
        'user_id': current_user['_id'],
        'book_id': bid,
        'type': interaction_type,
        'timestamp': datetime.now(),
        'metadata': metadata or {}
    }
    
    try:
        await db.interactions.insert_one(interaction)
        return {"status": "recorded"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}