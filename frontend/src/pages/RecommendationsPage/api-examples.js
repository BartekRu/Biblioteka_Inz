/**
 * api-examples.js - Przykładowe API calls i struktura danych
 *
 * Ten plik pokazuje jakie endpointy backend musi wspierać
 * oraz format zwracanych danych
 */

// ============================================================================
// SEKCJA A: TOP RECOMMENDATIONS
// ============================================================================

/**
 * Endpoint: GET /api/recommendations/lightgcn
 * Query params:
 *   - limit: number (default 30)
 *   - offset: number (default 0)
 *   - use_mmr: boolean (default true)
 *   - lambda_param: float 0-1 (default 0.7)
 *   - enforce_author_limit: boolean (default true)
 *   - max_per_author: number (default 2)
 */

const topRecommendationsResponse = {
  recommendations: [
    {
      _id: '507f1f77bcf86cd799439011',
      title: 'The Name of the Wind',
      author: 'Patrick Rothfuss',
      genres: ['Fantasy', 'Adventure'],
      description: 'A tale of magic, music, and mystery...',
      coverImage: 'https://example.com/cover.jpg',
      image_url: 'https://example.com/cover.jpg', // fallback
      small_image_url: 'https://example.com/small_cover.jpg', // fallback
      averageRating: 4.5,
      average_rating: 4.5, // fallback
      reviewCount: 2500,
      total_reviews: 2500, // fallback
      available: true,
      available_copies: 3,
      matchScore: 0.95, // Score z LightGCN (0-1)
      recommendationReason: 'Dopasowane do Twoich preferencji',
      recommendation_source: 'lightgcn',
      onWishlist: false,
    },
    // ... more books
  ],
  metadata: {
    diversity_metrics: {
      unique_genres: 8,
      unique_authors: 15,
      avg_pairwise_dissimilarity: 0.67, // 0-1, wyższe = bardziej różnorodne
    },
    total_count: 30,
    mmr_enabled: true,
    lambda_used: 0.7,
  },
};

// ============================================================================
// SEKCJA B1: BECAUSE YOU BORROWED
// ============================================================================

/**
 * Endpoint: GET /api/recommendations/because-borrowed
 * Returns: Sekcje z książkami podobnymi do ostatnio wypożyczonych
 */

const becauseBorrowedResponse = [
  {
    sourceBook: {
      _id: '507f1f77bcf86cd799439012',
      title: 'Harry Potter and the Sorcerer\'s Stone',
      author: 'J.K. Rowling',
      coverImage: 'https://example.com/hp1.jpg',
    },
    recommendations: [
      {
        _id: '507f1f77bcf86cd799439013',
        title: 'Percy Jackson & The Lightning Thief',
        author: 'Rick Riordan',
        // ... similar structure to topRecommendationsResponse
        matchScore: 0.88,
        recommendationReason: 'Podobna tematyka fantasy',
      },
      // ... more similar books
    ],
  },
  // ... more sections (up to 3-5)
];

// ============================================================================
// SEKCJA B2: GENRE RECOMMENDATIONS
// ============================================================================

/**
 * Endpoint: GET /api/recommendations/by-genre
 * Returns: Top gatunki użytkownika + spersonalizowane książki
 */

const genreRecommendationsResponse = [
  {
    genre: 'Fantasy',
    books: [
      {
        _id: '507f1f77bcf86cd799439014',
        title: 'The Way of Kings',
        author: 'Brandon Sanderson',
        genres: ['Fantasy', 'Epic'],
        matchScore: 0.92,
        // ... full book structure
      },
      // ... more books (10-20)
    ],
  },
  {
    genre: 'Science Fiction',
    books: [
      // ... books
    ],
  },
  // ... 2-3 top genres
];

// ============================================================================
// SEKCJA B3: AUTHOR RECOMMENDATIONS
// ============================================================================

/**
 * Endpoint: GET /api/recommendations/by-author
 * Returns: Książki od autorów które użytkownik lubi
 */

const authorRecommendationsResponse = [
  {
    author: 'Brandon Sanderson',
    books: [
      {
        _id: '507f1f77bcf86cd799439015',
        title: 'Mistborn: The Final Empire',
        author: 'Brandon Sanderson',
        matchScore: 0.89,
        // ... full book structure
      },
      // ... more books from this author
    ],
  },
  // ... 2-3 favorite authors
];

// ============================================================================
// SEKCJA B4: SIMILAR READERS
// ============================================================================

/**
 * Endpoint: GET /api/recommendations/similar-readers
 * Returns: Książki popularne wśród podobnych użytkowników
 */

const similarReadersResponse = {
  books: [
    {
      _id: '507f1f77bcf86cd799439016',
      title: 'Ender\'s Game',
      author: 'Orson Scott Card',
      matchScore: 0.87,
      popularityScore: 0.92, // jak popularna wśród podobnych użytkowników
      // ... full book structure
    },
    // ... more books (10-15)
  ],
  similar_user_count: 47, // ile podobnych użytkowników znaleziono
  metadata: {
    similarity_threshold: 0.7, // jaki threshold podobieństwa
  },
};

// ============================================================================
// SEKCJA C1: DIVERSE DISCOVERY
// ============================================================================

/**
 * Endpoint: GET /api/recommendations/lightgcn (with low lambda)
 * Query params: use_mmr=true, lambda_param=0.3
 * Returns: Wysoce zróżnicowane rekomendacje
 */

const diverseDiscoveryResponse = {
  recommendations: [
    // ... books with high diversity
  ],
  metadata: {
    diversity_metrics: {
      unique_genres: 10,
      unique_authors: 10,
      avg_pairwise_dissimilarity: 0.85, // higher than normal
    },
  },
};

// ============================================================================
// SEKCJA C2: NEW ARRIVALS
// ============================================================================

/**
 * Endpoint: GET /api/recommendations/new-arrivals
 * Returns: Nowe książki w bibliotece z personalizacją
 */

const newArrivalsResponse = [
  {
    _id: '507f1f77bcf86cd799439017',
    title: 'The Fragile Threads of Power',
    author: 'V.E. Schwab',
    addedDate: '2025-01-20T10:00:00Z',
    matchScore: 0.81, // based on content similarity
    coldStart: true, // flag indicating it's a new book
    // ... full book structure
  },
  // ... more new books (10-20)
];

// ============================================================================
// SEKCJA C3: LIBRARIAN PICKS
// ============================================================================

/**
 * Endpoint: GET /api/recommendations/librarian-picks
 * Returns: Książki wybrane przez bibliotekarzy + personalizacja
 */

const librarianPicksResponse = {
  books: [
    {
      _id: '507f1f77bcf86cd799439018',
      title: 'Project Hail Mary',
      author: 'Andy Weir',
      matchScore: 0.88,
      curatorNote: 'Świetna nauka + przygoda!',
      // ... full book structure
    },
    // ... more curated books (5-10)
  ],
  curator: {
    name: 'Maria Kowalska',
    role: 'Bibliotekarz',
    specialty: 'Fantastyka naukowa',
  },
};

// ============================================================================
// MODEL METRICS
// ============================================================================

/**
 * Endpoint: GET /api/recommendations/metrics
 * Returns: Metryki modelu LightGCN
 */

const modelMetricsResponse = {
  model_name: 'LightGCN',
  version: '1.0.0',
  last_training_date: '2025-01-20T00:00:00Z',
  interactions: 932940, // total interactions used for training
  unique_users: 53424,
  unique_books: 10000,
  metrics: {
    'recall@10': 0.1234,
    'recall@20': 0.1411,
    'ndcg@10': 0.0621,
    'ndcg@20': 0.0842,
  },
  embedding_dim: 64,
  num_layers: 3,
};

// ============================================================================
// INTERACTION TRACKING
// ============================================================================

/**
 * Endpoint: POST /api/interactions
 * Body: { book_id, interaction_type, metadata }
 */

const interactionRequest = {
  book_id: '507f1f77bcf86cd799439011',
  interaction_type: 'view', // 'view' | 'borrow' | 'review' | 'wishlist_add' | 'wishlist_remove'
  metadata: {
    source: 'top-recommendations',
    mmr_enabled: true,
    lambda_used: 0.7,
    position: 3, // position in list
    timestamp: '2025-01-25T14:30:00Z',
  },
};

const interactionResponse = {
  success: true,
  interaction_id: '507f1f77bcf86cd799439099',
  message: 'Interaction recorded successfully',
};

// ============================================================================
// PRZYKŁADOWE API CLASS
// ============================================================================

class RecommendationsAPI {
  /**
   * Pobierz główne rekomendacje LightGCN
   */
  async getUserLightGCN(limit = 30, offset = 0, useMmr = true, lambda = 0.7, enforceAuthorLimit = true, maxPerAuthor = 2) {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
      use_mmr: useMmr.toString(),
      lambda_param: lambda.toString(),
      enforce_author_limit: enforceAuthorLimit.toString(),
      max_per_author: maxPerAuthor.toString(),
    });

    const response = await fetch(`/api/recommendations/lightgcn?${params}`);
    return response.json();
  }

  /**
   * Pobierz rekomendacje "ponieważ wypożyczyłeś"
   */
  async getBecauseYouBorrowed() {
    const response = await fetch('/api/recommendations/because-borrowed');
    return response.json();
  }

  /**
   * Pobierz rekomendacje według gatunku
   */
  async getGenreRecommendations() {
    const response = await fetch('/api/recommendations/by-genre');
    return response.json();
  }

  /**
   * Pobierz rekomendacje według autora
   */
  async getAuthorRecommendations() {
    const response = await fetch('/api/recommendations/by-author');
    return response.json();
  }

  /**
   * Pobierz książki od podobnych czytelników
   */
  async getSimilarReadersBooks() {
    const response = await fetch('/api/recommendations/similar-readers');
    return response.json();
  }

  /**
   * Pobierz nowości w bibliotece
   */
  async getNewArrivals() {
    const response = await fetch('/api/recommendations/new-arrivals');
    return response.json();
  }

  /**
   * Pobierz wybrane przez bibliotekarzy
   */
  async getLibrarianPicks() {
    const response = await fetch('/api/recommendations/librarian-picks');
    return response.json();
  }

  /**
   * Pobierz metryki modelu
   */
  async getModelMetrics() {
    const response = await fetch('/api/recommendations/metrics');
    return response.json();
  }

  /**
   * Zgłoś interakcję użytkownika
   */
  async reportInteraction(bookId, interactionType, metadata = {}) {
    const response = await fetch('/api/interactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        book_id: bookId,
        interaction_type: interactionType,
        metadata: {
          ...metadata,
          timestamp: new Date().toISOString(),
        },
      }),
    });
    return response.json();
  }
}

export default RecommendationsAPI;

// ============================================================================
// CHECKLIST DLA BACKENDU
// ============================================================================

/*
Backend TODO List:

[ ] GET  /api/recommendations/lightgcn
    - Parametry: limit, offset, use_mmr, lambda_param, enforce_author_limit, max_per_author
    - Zwraca: { recommendations: [...], metadata: {...} }

[ ] GET  /api/recommendations/because-borrowed
    - Zwraca: [{ sourceBook: {...}, recommendations: [...] }]

[ ] GET  /api/recommendations/by-genre
    - Zwraca: [{ genre: "...", books: [...] }]

[ ] GET  /api/recommendations/by-author
    - Zwraca: [{ author: "...", books: [...] }]

[ ] GET  /api/recommendations/similar-readers
    - Zwraca: { books: [...], similar_user_count: number }

[ ] GET  /api/recommendations/new-arrivals
    - Zwraca: [{ ...book, addedDate, coldStart: true }]

[ ] GET  /api/recommendations/librarian-picks
    - Zwraca: { books: [...], curator: {...} }

[ ] GET  /api/recommendations/metrics
    - Zwraca: { model_name, metrics, interactions, ... }

[x] POST /api/interactions
    - Body: { book_id, interaction_type, metadata }
    - Zwraca: { success: boolean }

Existing endpoints (już działają):
[x] GET /api/recommendations/lightgcn (basic)
[x] POST /api/interactions (basic)

*/
