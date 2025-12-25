// services/api.js - CLEAN & ORGANIZED

import axios from 'axios';

// ============================================================================
// AXIOS SETUP
// ============================================================================

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to every request
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle 401 errors (expired token)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ============================================================================
// RECOMMENDATIONS API
// ============================================================================

export const recommendationsAPI = {
  // ─────────────────────────────────────────────────────────────────────────
  // CORE RECOMMENDATIONS
  // ─────────────────────────────────────────────────────────────────────────

  /**
   * Główne rekomendacje LightGCN + MMR
   */
  getUserLightGCN: (
    limit = 20,
    offset = 0,
    useMmr = true,
    lambdaParam = 0.7,
    enforceAuthorLimit = true,
    maxPerAuthor = 2
  ) => {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
      use_mmr: useMmr.toString(),
      lambda_param: lambdaParam.toString(),
      enforce_author_limit: enforceAuthorLimit.toString(),
      max_per_author: maxPerAuthor.toString(),
    });

    return apiClient.get(`/v1/recommendations/user-lightgcn?${params.toString()}`);
  },

  /**
   * Wyróżnione książki
   */
  getFeatured: (limit = 10) => {
    return apiClient.get(`/v1/recommendations/featured?limit=${limit}`);
  },

  /**
   * Kategorie z przykładowymi okładkami
   */
  getCategories: () => {
    return apiClient.get('/v1/recommendations/categories');
  },

  /**
   * Kolejka odkryć
   */
  getDiscoveryQueue: (limit = 12) => {
    return apiClient.get(`/v1/recommendations/discovery-queue?limit=${limit}`);
  },

  /**
   * Znani autorzy
   */
  getKnownAuthors: (limit = 6) => {
    return apiClient.get(`/v1/recommendations/known-authors?limit=${limit}`);
  },

  /**
   * Podobne książki do danej książki
   */
  getSimilar: (bookId, limit = 8) => {
    return apiClient.get(`/v1/recommendations/similar/${bookId}?limit=${limit}`);
  },

  // ─────────────────────────────────────────────────────────────────────────
  // SEKCJA B: EXPLAINABLE RECOMMENDATIONS
  // ─────────────────────────────────────────────────────────────────────────

  /**
   * "Ponieważ wypożyczyłeś X" - item-item similarity
   */
  getBecauseYouBorrowed: (limit = 3) => {
    return apiClient.get(`/v1/recommendations/because-borrowed?limit=${limit}`);
  },

  /**
   * Rekomendacje według gatunku
   */
  getGenreRecommendations: async (limit = 3, booksPerGenre = 10) => {
    try {
      const response = await apiClient.get('/v1/recommendations/by-genre', {
        params: { limit, books_per_genre: booksPerGenre },
      });
      return response;
    } catch (error) {
      if (error.response?.status === 404) {
        console.warn('⚠️ Endpoint /by-genre not implemented yet');
        return { data: [] };
      }
      throw error;
    }
  },

  /**
   * Rekomendacje według autora
   */
  getAuthorRecommendations: async (limit = 3, booksPerAuthor = 10) => {
    try {
      const response = await apiClient.get('/v1/recommendations/by-author', {
        params: { limit, books_per_author: booksPerAuthor },
      });
      return response;
    } catch (error) {
      if (error.response?.status === 404) {
        console.warn('⚠️ Endpoint /by-author not implemented yet');
        return { data: [] };
      }
      throw error;
    }
  },

  /**
   * Książki od podobnych czytelników (user-based CF)
   */
  getSimilarReadersBooks: async (limit = 15) => {
    try {
      const response = await apiClient.get('/v1/recommendations/similar-readers', {
        params: { limit },
      });
      return response;
    } catch (error) {
      if (error.response?.status === 404) {
        console.warn('⚠️ Endpoint /similar-readers not implemented yet');
        return { data: { books: [], similar_user_count: 0 } };
      }
      throw error;
    }
  },

  // ─────────────────────────────────────────────────────────────────────────
  // SEKCJA C: DISCOVERY
  // ─────────────────────────────────────────────────────────────────────────

  /**
   * Nowości w bibliotece (cold-start handling)
   */
  getNewArrivals: async (limit = 20, days = 30) => {
    try {
      const response = await apiClient.get('/v1/recommendations/new-arrivals', {
        params: { limit, days },
      });
      return response;
    } catch (error) {
      if (error.response?.status === 404) {
        console.warn('⚠️ Endpoint /new-arrivals not implemented yet');
        return { data: [] };
      }
      throw error;
    }
  },

  /**
   * Ukryte skarby - mało popularne, wysoko oceniane
   */
  getHiddenGems: async (limit = 15) => {
    try {
      const response = await apiClient.get('/v1/recommendations/hidden-gems', {
        params: { limit },
      });
      return response;
    } catch (error) {
      if (error.response?.status === 404) {
        console.warn('⚠️ Endpoint /hidden-gems not implemented yet');
        return { data: [] };
      }
      throw error;
    }
  },

  /**
   * Wysoko oceniane odkrycia - top-rated w ulubionych gatunkach
   */
  getHighlyRated: async (limit = 15, minRating = 4.5) => {
    try {
      const response = await apiClient.get('/v1/recommendations/highly-rated', {
        params: { limit, min_rating: minRating },
      });
      return response;
    } catch (error) {
      if (error.response?.status === 404) {
        console.warn('⚠️ Endpoint /highly-rated not implemented yet');
        return { data: [] };
      }
      throw error;
    }
  },

  // ─────────────────────────────────────────────────────────────────────────
  // INTERACTIONS & TRACKING
  // ─────────────────────────────────────────────────────────────────────────

  /**
   * Raportuje interakcję użytkownika
   * Unified endpoint - wszystkie interakcje do jednej kolekcji
   */
  reportInteraction: (bookId, interactionType, metadata = {}) => {
    return apiClient.post('/v1/recommendations/interaction', {
      book_id: bookId,
      interaction_type: interactionType,
      metadata,
    });
  },

  // ─────────────────────────────────────────────────────────────────────────
  // METRICS & DEBUG
  // ─────────────────────────────────────────────────────────────────────────

  /**
   * Metryki modelu LightGCN
   */
  getModelMetrics: () => {
    return apiClient.get('/v1/recommendations/metrics');
  },

  /**
   * Status systemu rekomendacji
   */
  getHealth: () => {
    return apiClient.get('/v1/recommendations/health');
  },

  /**
   * Porównanie różnorodności dla różnych lambda
   */
  getDiversityComparison: (n = 30, lambdaValues = '0.3,0.5,0.7,0.9') => {
    return apiClient.get('/v1/recommendations/diversity-comparison', {
      params: { n, lambda_values: lambdaValues },
    });
  },

  /**
   * Statystyki embeddingów
   */
  getEmbeddingStats: () => {
    return apiClient.get('/v1/recommendations/embedding-stats');
  },

  /**
   * Statystyki użytkownika (debug)
   */
  getUserStats: (userId) => {
    return apiClient.get(`/v1/recommendations/debug/user-stats/${userId}`);
  },

  /**
   * Statystyki serwisu (admin only)
   */
  getServiceStats: () => {
    return apiClient.get('/v1/recommendations/debug/service-stats');
  },
};

// ============================================================================
// BOOKS API
// ============================================================================

export const booksAPI = {
  getAll: (params = {}) => {
    return apiClient.get('/v1/books', { params });
  },

  getById: (id) => {
    return apiClient.get(`/v1/books/${id}`);
  },

  search: (query, filters = {}) => {
    return apiClient.get('/v1/books/search', {
      params: { q: query, ...filters },
    });
  },

  getByGenre: (genre, limit = 20) => {
    return apiClient.get('/v1/books', {
      params: { genre, limit },
    });
  },

  getByAuthor: (author, limit = 20) => {
    return apiClient.get('/v1/books', {
      params: { author, limit },
    });
  },
};

// ============================================================================
// AUTH API
// ============================================================================

export const authAPI = {
  login: (credentials) => {
    return apiClient.post('/v1/auth/login', credentials);
  },

  register: (userData) => {
    return apiClient.post('/v1/auth/register', userData);
  },

  logout: () => {
    localStorage.removeItem('token');
    return Promise.resolve();
  },

  getCurrentUser: () => {
    return apiClient.get('/v1/auth/me');
  },

  updateProfile: (data) => {
    return apiClient.put('/v1/auth/profile', data);
  },
};

// ============================================================================
// LOANS API
// ============================================================================

export const loansAPI = {
  /**
   * Wypożycz książkę
   */
  borrow: (bookIdOrObject) => {
    const bookId =
      typeof bookIdOrObject === 'string' ? bookIdOrObject : bookIdOrObject._id || bookIdOrObject.id;
    return apiClient.post('/v1/loans/borrow', { book_id: String(bookId) });
  },

  /**
   * Alias dla borrow() - kompatybilność z BookDetails.jsx
   */
  create: (bookIdOrObject) => {
    const bookId =
      typeof bookIdOrObject === 'string' ? bookIdOrObject : bookIdOrObject._id || bookIdOrObject.id;
    return apiClient.post('/v1/loans/borrow', { book_id: String(bookId) });
  },

  /**
   * Zwróć książkę
   */
  return: (loanId) => {
    return apiClient.post(`/v1/loans/${loanId}/return`);
  },

  /**
   * Pobierz wypożyczenia zalogowanego użytkownika
   */
  getMine: (status = null) => {
    const params = status ? { status } : {};
    return apiClient.get('/v1/loans/me', { params });
  },

  /**
   * Alias dla getMine
   */
  getUserLoans: (status = null) => {
    const params = status ? { status } : {};
    return apiClient.get('/v1/loans/me', { params });
  },

  /**
   * Przedłuż wypożyczenie
   */
  renew: (loanId) => {
    return apiClient.post(`/v1/loans/${loanId}/renew`);
  },
};

// ============================================================================
// REVIEWS API
// ============================================================================

export const reviewsAPI = {
  /**
   * Dodaj recenzję
   */
  create: (bookId, rating, content = '') => {
    return apiClient.post('/v1/reviews', {
      book_id: String(bookId),
      rating: Number(rating),
      content: String(content),
    });
  },

  /**
   * Pobierz recenzje dla książki
   */
  getByBook: (bookId) => {
    return apiClient.get(`/v1/reviews/book/${bookId}`);
  },

  /**
   * Pobierz recenzje użytkownika
   */
  getUserReviews: () => {
    return apiClient.get('/v1/reviews/user');
  },

  /**
   * Zaktualizuj recenzję
   */
  update: (reviewId, data) => {
    return apiClient.put(`/v1/reviews/${reviewId}`, data);
  },

  /**
   * Usuń recenzję
   */
  delete: (reviewId) => {
    return apiClient.delete(`/v1/reviews/${reviewId}`);
  },
};

// ============================================================================
// WISHLIST API
// ============================================================================

export const wishlistAPI = {
  add: (bookId) => {
    return recommendationsAPI.reportInteraction(bookId, 'wishlist_add');
  },

  remove: (bookId) => {
    return recommendationsAPI.reportInteraction(bookId, 'wishlist_remove');
  },

  getAll: () => {
    return apiClient.get('/v1/wishlist');
  },
};

// ============================================================================
// STATS API
// ============================================================================

export const statsAPI = {
  getOverview: () => {
    return apiClient.get('/v1/stats/overview');
  },

  getUserActivity: (userId, dateRange) => {
    return apiClient.get(`/v1/stats/user/${userId}`, {
      params: dateRange,
    });
  },

  getPopularBooks: (limit = 10) => {
    return apiClient.get('/v1/stats/popular-books', {
      params: { limit },
    });
  },
};

// ============================================================================
// USERS API
// ============================================================================

export const usersAPI = {
  /**
   * Profil użytkownika
   */
  getMe: () => {
    return authAPI.getCurrentUser();
  },

  /**
   * Alias dla getMe
   */
  getProfile: () => {
    return authAPI.getCurrentUser();
  },

  /**
   * Statystyki użytkownika
   */
  getUserStats: async () => {
    try {
      return await apiClient.get('/v1/users/me/stats');
    } catch (err) {
      console.log('Using embedding-stats as fallback for user stats');
      return await recommendationsAPI.getEmbeddingStats();
    }
  },

  /**
   * Zaktualizuj preferencje
   */
  updatePreferences: (preferences) => {
    return apiClient.put('/v1/users/me/preferences', preferences);
  },

  /**
   * Historia aktywności
   */
  getActivityHistory: (params = {}) => {
    return apiClient.get('/v1/users/me/activity', { params });
  },

  /**
   * Ulubione gatunki
   */
  getFavoriteGenres: () => {
    return apiClient.get('/v1/users/me/favorite-genres');
  },
};

export default apiClient;
