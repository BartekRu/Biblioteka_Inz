# 🔌 Backend API Specification for Recommendations System

## Overview

Ten dokument opisuje wszystkie endpointy API wymagane przez zrefaktoryzowany system rekomendacji.

**Base URL:** `/api/recommendations`

**Authentication:** Wszystkie endpointy wymagają JWT token w header:
```
Authorization: Bearer <jwt_token>
```

---

## 📊 Endpoints Overview

| Priority | Endpoint | Method | Status | Description |
|----------|----------|--------|--------|-------------|
| 🟢 P1 | `/lightgcn` | GET | ✅ Implemented | Główne rekomendacje LightGCN |
| 🟢 P1 | `/interactions` | POST | ✅ Implemented | Track user interactions |
| 🟡 P2 | `/because-borrowed` | GET | ⏳ To Do | "Ponieważ wypożyczyłeś..." |
| 🟡 P2 | `/by-genre` | GET | ⏳ To Do | Rekomendacje według gatunku |
| 🟡 P2 | `/by-author` | GET | ⏳ To Do | Rekomendacje według autora |
| 🟡 P2 | `/similar-readers` | GET | ⏳ To Do | Od podobnych czytelników |
| 🔴 P3 | `/new-arrivals` | GET | ⏳ To Do | Nowości w bibliotece |
| 🔴 P3 | `/librarian-picks` | GET | ⏳ To Do | Wybór bibliotekarzy |
| 🔴 P3 | `/metrics` | GET | ⏳ To Do | Metryki modelu |

---

## 🎯 Priority 1 Endpoints (Required)

### 1. GET `/api/recommendations/lightgcn`

**Opis:** Główne rekomendacje z modelu LightGCN z opcjonalnym MMR re-rankingiem.

**Query Parameters:**
```typescript
{
  limit?: number;           // default: 30, max: 100
  offset?: number;          // default: 0
  use_mmr?: boolean;        // default: true
  lambda_param?: float;     // default: 0.7, range: 0.0-1.0
  enforce_author_limit?: boolean;  // default: true
  max_per_author?: number;  // default: 2, range: 1-10
}
```

**Example Request:**
```bash
GET /api/recommendations/lightgcn?limit=30&use_mmr=true&lambda_param=0.7
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response 200 OK:**
```json
{
  "recommendations": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "title": "The Name of the Wind",
      "author": "Patrick Rothfuss",
      "genres": ["Fantasy", "Adventure"],
      "description": "A tale of magic, music, and mystery...",
      "coverImage": "https://example.com/cover.jpg",
      "averageRating": 4.5,
      "reviewCount": 2500,
      "available": true,
      "available_copies": 3,
      "matchScore": 0.95,
      "recommendationReason": "Dopasowane do Twoich preferencji",
      "recommendation_source": "lightgcn"
    }
  ],
  "metadata": {
    "total_count": 30,
    "diversity_metrics": {
      "unique_genres": 8,
      "unique_authors": 15,
      "avg_pairwise_dissimilarity": 0.67
    },
    "mmr_enabled": true,
    "lambda_used": 0.7
  }
}
```

**Python Implementation (FastAPI):**
```python
from fastapi import APIRouter, Depends, Query
from typing import Optional

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

@router.get("/lightgcn")
async def get_lightgcn_recommendations(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    use_mmr: bool = Query(True),
    lambda_param: float = Query(0.7, ge=0.0, le=1.0),
    enforce_author_limit: bool = Query(True),
    max_per_author: int = Query(2, ge=1, le=10),
    current_user: User = Depends(get_current_user)
):
    """
    Get personalized LightGCN recommendations with optional MMR re-ranking
    """
    # 1. Get user embedding from LightGCN model
    user_embedding = lightgcn_model.get_user_embedding(current_user.id)
    
    # 2. Get candidate books (top N by cosine similarity)
    candidates = lightgcn_model.recommend(
        user_embedding,
        k=limit * 3  # Get more candidates for MMR
    )
    
    # 3. Apply MMR re-ranking if enabled
    if use_mmr:
        candidates = mmr_rerank(
            candidates,
            lambda_param=lambda_param,
            enforce_author_limit=enforce_author_limit,
            max_per_author=max_per_author
        )
    
    # 4. Apply author limit if enabled
    if enforce_author_limit and not use_mmr:
        candidates = apply_author_limit(candidates, max_per_author)
    
    # 5. Slice to requested limit
    recommendations = candidates[offset:offset+limit]
    
    # 6. Calculate diversity metrics
    diversity_metrics = calculate_diversity(recommendations)
    
    return {
        "recommendations": recommendations,
        "metadata": {
            "total_count": len(recommendations),
            "diversity_metrics": diversity_metrics,
            "mmr_enabled": use_mmr,
            "lambda_used": lambda_param if use_mmr else None
        }
    }
```

---

### 2. POST `/api/interactions`

**Opis:** Zapisz interakcję użytkownika z książką (view, borrow, review, etc.)

**Request Body:**
```json
{
  "book_id": "507f1f77bcf86cd799439011",
  "interaction_type": "view",
  "metadata": {
    "source": "top-recommendations",
    "mmr_enabled": true,
    "lambda_used": 0.7,
    "position": 3,
    "timestamp": "2025-01-25T14:30:00Z"
  }
}
```

**Interaction Types:**
- `view` - Użytkownik obejrzał szczegóły książki
- `borrow` - Użytkownik wypożyczył książkę
- `review` - Użytkownik dodał recenzję
- `wishlist_add` - Dodano do listy życzeń
- `wishlist_remove` - Usunięto z listy życzeń

**Response 200 OK:**
```json
{
  "success": true,
  "interaction_id": "507f1f77bcf86cd799439099",
  "message": "Interaction recorded successfully"
}
```

**Python Implementation:**
```python
@router.post("/interactions")
async def record_interaction(
    interaction: InteractionCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Record user interaction for analytics and model improvement
    """
    # Save to database
    db_interaction = await InteractionService.create(
        user_id=current_user.id,
        book_id=interaction.book_id,
        interaction_type=interaction.interaction_type,
        metadata=interaction.metadata
    )
    
    # Trigger async update of model (if needed)
    if interaction.interaction_type in ['borrow', 'review']:
        background_tasks.add_task(update_model_incrementally, db_interaction)
    
    return {
        "success": True,
        "interaction_id": str(db_interaction.id),
        "message": "Interaction recorded successfully"
    }
```

---

## 🟡 Priority 2 Endpoints (Explainable Recommendations - Section B)

### 3. GET `/api/recommendations/because-borrowed`

**Opis:** Sekcje "Ponieważ wypożyczyłeś X" - podobne książki do ostatnio wypożyczonych.

**Query Parameters:**
```typescript
{
  limit?: number;  // default: 3, limit sekcji
  books_per_section?: number;  // default: 10
}
```

**Response 200 OK:**
```json
[
  {
    "sourceBook": {
      "_id": "507f1f77bcf86cd799439012",
      "title": "Harry Potter and the Sorcerer's Stone",
      "author": "J.K. Rowling",
      "coverImage": "https://example.com/hp1.jpg"
    },
    "recommendations": [
      {
        "_id": "507f1f77bcf86cd799439013",
        "title": "Percy Jackson & The Lightning Thief",
        "author": "Rick Riordan",
        "matchScore": 0.88,
        "recommendationReason": "Podobna tematyka fantasy",
        "similarityScore": 0.91
      }
    ]
  }
]
```

**Python Implementation:**
```python
@router.get("/because-borrowed")
async def get_because_borrowed(
    limit: int = Query(3, ge=1, le=10),
    books_per_section: int = Query(10, ge=5, le=20),
    current_user: User = Depends(get_current_user)
):
    """
    Get "Because you borrowed X" recommendations using item-item similarity
    """
    # 1. Get recent borrows (last 30 days)
    recent_borrows = await get_user_recent_borrows(
        current_user.id,
        days=30,
        limit=limit
    )
    
    sections = []
    for borrowed_book in recent_borrows:
        # 2. Get book embedding from LightGCN
        book_embedding = lightgcn_model.get_item_embedding(borrowed_book.id)
        
        # 3. Find similar books by cosine similarity
        similar_books = lightgcn_model.find_similar_items(
            book_embedding,
            k=books_per_section,
            exclude_ids=[borrowed_book.id]  # Don't recommend same book
        )
        
        # 4. Add similarity scores
        for book in similar_books:
            book['similarityScore'] = cosine_similarity(
                book_embedding,
                lightgcn_model.get_item_embedding(book['_id'])
            )
        
        sections.append({
            "sourceBook": borrowed_book,
            "recommendations": similar_books
        })
    
    return sections
```

---

### 4. GET `/api/recommendations/by-genre`

**Opis:** Rekomendacje filtrowane przez top gatunki użytkownika.

**Query Parameters:**
```typescript
{
  limit?: number;  // default: 3, liczba gatunków
  books_per_genre?: number;  // default: 10
}
```

**Response 200 OK:**
```json
[
  {
    "genre": "Fantasy",
    "books": [
      {
        "_id": "507f1f77bcf86cd799439014",
        "title": "The Way of Kings",
        "author": "Brandon Sanderson",
        "genres": ["Fantasy", "Epic"],
        "matchScore": 0.92
      }
    ],
    "user_preference_score": 0.85
  }
]
```

**Python Implementation:**
```python
@router.get("/by-genre")
async def get_genre_recommendations(
    limit: int = Query(3, ge=1, le=5),
    books_per_genre: int = Query(10, ge=5, le=20),
    current_user: User = Depends(get_current_user)
):
    """
    Get recommendations filtered by user's favorite genres
    """
    # 1. Analyze user's genre preferences
    genre_preferences = await analyze_user_genre_preferences(current_user.id)
    top_genres = genre_preferences[:limit]
    
    sections = []
    for genre_pref in top_genres:
        # 2. Get all books in this genre
        genre_books = await get_books_by_genre(genre_pref['genre'])
        
        # 3. Personalize ranking using LightGCN
        user_embedding = lightgcn_model.get_user_embedding(current_user.id)
        
        ranked_books = []
        for book in genre_books:
            book_embedding = lightgcn_model.get_item_embedding(book.id)
            score = cosine_similarity(user_embedding, book_embedding)
            ranked_books.append((book, score))
        
        # 4. Sort by score and take top N
        ranked_books.sort(key=lambda x: x[1], reverse=True)
        top_books = [book for book, score in ranked_books[:books_per_genre]]
        
        sections.append({
            "genre": genre_pref['genre'],
            "books": top_books,
            "user_preference_score": genre_pref['score']
        })
    
    return sections
```

---

### 5. GET `/api/recommendations/by-author`

**Opis:** Rekomendacje od autorów których użytkownik lubi.

**Response podobny do `/by-genre`, ale z autorami zamiast gatunków.**

---

### 6. GET `/api/recommendations/similar-readers`

**Opis:** Książki popularne wśród podobnych czytelników (user-based CF).

**Response 200 OK:**
```json
{
  "books": [
    {
      "_id": "507f1f77bcf86cd799439016",
      "title": "Ender's Game",
      "author": "Orson Scott Card",
      "matchScore": 0.87,
      "popularityScore": 0.92
    }
  ],
  "similar_user_count": 47,
  "metadata": {
    "similarity_threshold": 0.7
  }
}
```

**Python Implementation:**
```python
@router.get("/similar-readers")
async def get_similar_readers_books(
    limit: int = Query(15, ge=5, le=30),
    current_user: User = Depends(get_current_user)
):
    """
    Get books popular among similar readers (user-based CF)
    """
    # 1. Get user embedding
    user_embedding = lightgcn_model.get_user_embedding(current_user.id)
    
    # 2. Find similar users by embedding similarity
    similar_users = lightgcn_model.find_similar_users(
        user_embedding,
        k=50,  # Top 50 similar users
        threshold=0.7
    )
    
    # 3. Get books they borrowed/liked
    similar_users_books = await get_books_from_users(
        [u['user_id'] for u in similar_users]
    )
    
    # 4. Rank by popularity among similar users
    book_popularity = {}
    for book in similar_users_books:
        book_popularity[book.id] = book_popularity.get(book.id, 0) + 1
    
    # 5. Sort and return
    ranked_books = sorted(
        book_popularity.items(),
        key=lambda x: x[1],
        reverse=True
    )[:limit]
    
    books = [await get_book_details(book_id) for book_id, _ in ranked_books]
    
    return {
        "books": books,
        "similar_user_count": len(similar_users),
        "metadata": {
            "similarity_threshold": 0.7
        }
    }
```

---

## 🔴 Priority 3 Endpoints (Discovery - Section C)

### 7. GET `/api/recommendations/new-arrivals`

**Opis:** Nowości w bibliotece z personalizacją (cold-start handling).

**Response 200 OK:**
```json
[
  {
    "_id": "507f1f77bcf86cd799439017",
    "title": "The Fragile Threads of Power",
    "author": "V.E. Schwab",
    "addedDate": "2025-01-20T10:00:00Z",
    "matchScore": 0.81,
    "coldStart": true,
    "similarityMethod": "content-based"
  }
]
```

**Python Implementation:**
```python
@router.get("/new-arrivals")
async def get_new_arrivals(
    limit: int = Query(20, ge=5, le=50),
    days: int = Query(30, ge=7, le=90),
    current_user: User = Depends(get_current_user)
):
    """
    Get new books with personalized ranking (cold-start handling)
    """
    # 1. Get recently added books
    cutoff_date = datetime.now() - timedelta(days=days)
    new_books = await Book.find(
        Book.addedDate >= cutoff_date
    ).to_list()
    
    # 2. For each book, calculate content-based similarity
    user_profile = await build_user_content_profile(current_user.id)
    
    ranked_books = []
    for book in new_books:
        # Calculate similarity based on:
        # - Genre overlap
        # - Author familiarity
        # - Description TF-IDF similarity
        score = calculate_content_similarity(book, user_profile)
        
        book_dict = book.dict()
        book_dict['matchScore'] = score
        book_dict['coldStart'] = True
        book_dict['similarityMethod'] = 'content-based'
        
        ranked_books.append((book_dict, score))
    
    # 3. Sort and return
    ranked_books.sort(key=lambda x: x[1], reverse=True)
    return [book for book, _ in ranked_books[:limit]]
```

---

### 8. GET `/api/recommendations/librarian-picks`

**Opis:** Książki wybrane przez bibliotekarzy + personalizacja AI.

**Response 200 OK:**
```json
{
  "books": [
    {
      "_id": "507f1f77bcf86cd799439018",
      "title": "Project Hail Mary",
      "author": "Andy Weir",
      "matchScore": 0.88,
      "curatorNote": "Świetna nauka + przygoda!",
      "featured": true
    }
  ],
  "curator": {
    "name": "Maria Kowalska",
    "role": "Bibliotekarz",
    "specialty": "Fantastyka naukowa"
  }
}
```

---

### 9. GET `/api/recommendations/metrics`

**Opis:** Metryki modelu LightGCN.

**Response 200 OK:**
```json
{
  "model_name": "LightGCN",
  "version": "1.0.0",
  "last_training_date": "2025-01-20T00:00:00Z",
  "interactions": 932940,
  "unique_users": 53424,
  "unique_books": 10000,
  "metrics": {
    "recall@10": 0.1234,
    "recall@20": 0.1411,
    "ndcg@10": 0.0621,
    "ndcg@20": 0.0842
  },
  "embedding_dim": 64,
  "num_layers": 3
}
```

---

## 🔧 Error Responses

Wszystkie endpointy mogą zwrócić następujące błędy:

**401 Unauthorized:**
```json
{
  "detail": "Not authenticated"
}
```

**404 Not Found:**
```json
{
  "detail": "User not found"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error",
  "error": "Model not loaded"
}
```

---

## 🧪 Testing Endpoints

### Przykładowy test z curl:

```bash
# 1. Login
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}' \
  | jq -r '.access_token')

# 2. Get recommendations
curl -X GET "http://localhost:8000/api/recommendations/lightgcn?limit=10&use_mmr=true" \
  -H "Authorization: Bearer $TOKEN" \
  | jq

# 3. Record interaction
curl -X POST http://localhost:8000/api/interactions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "507f1f77bcf86cd799439011",
    "interaction_type": "view",
    "metadata": {"source": "test"}
  }' \
  | jq
```

---

## 📊 Database Schema Requirements

### Interactions Collection
```javascript
{
  _id: ObjectId,
  user_id: ObjectId,
  book_id: ObjectId,
  interaction_type: String, // 'view' | 'borrow' | 'review' | ...
  metadata: {
    source: String,
    mmr_enabled: Boolean,
    lambda_used: Number,
    position: Number,
    // ... custom fields
  },
  timestamp: Date,
  created_at: Date
}
```

### Books Collection (rozszerzone pola)
```javascript
{
  _id: ObjectId,
  title: String,
  author: String,
  genres: [String],
  description: String,
  coverImage: String,
  averageRating: Number,
  reviewCount: Number,
  available_copies: Number,
  addedDate: Date,  // 🆕 dla new-arrivals
  featured: Boolean, // 🆕 dla librarian-picks
  curatorNote: String, // 🆕 dla librarian-picks
  // ... existing fields
}
```

---

**Version:** 2.0  
**Last Updated:** 2025-01-25  
**Author:** Biblioteka_Inz Team
