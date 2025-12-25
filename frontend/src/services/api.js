// services/api.js - UPDATED WITH MMR SUPPORT

import axios from 'axios';

// Base URL z zmiennej środowiskowej lub domyślna
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Axios instance z automatycznym dodawaniem tokena
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor dodający token do każdego requesta
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

// Interceptor do obsługi błędów
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token wygasł - wyloguj użytkownika
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ============================================================================
// RECOMMENDATIONS API - UPDATED WITH MMR
// ============================================================================

export const recommendationsAPI = {
  /**
   * Pobiera rekomendacje LightGCN z opcjonalnym MMR re-ranking
   * 
   * @param {number} limit - Liczba rekomendacji (domyślnie 20)
   * @param {number} offset - Offset dla paginacji/rotacji (domyślnie 0)
   * @param {boolean} useMmr - Czy użyć MMR re-ranking (domyślnie true)
   * @param {number} lambdaParam - Balans trafność/różnorodność 0.0-1.0 (domyślnie 0.7)
   * @param {boolean} enforceAuthorLimit - Czy ograniczać autorów (domyślnie true)
   * @param {number} maxPerAuthor - Max książek od autora (domyślnie 2)
   * @returns {Promise} Response z { recommendations: [...], metadata: {...} }
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
   * Pobiera wyróżnione książki dopasowane do użytkownika
   */
  getFeatured: (limit = 10) => {
    return apiClient.get(`/v1/recommendations/featured?limit=${limit}`);
  },

  /**
   * Pobiera kategorie książek z przykładowymi okładkami
   */
  getCategories: () => {
    return apiClient.get('/v1/recommendations/categories');
  },

  /**
   * Pobiera sekcje "Ponieważ wypożyczyłeś X"
   */
  getBecauseYouBorrowed: (limit = 3) => {
    return apiClient.get(`/v1/recommendations/because-borrowed?limit=${limit}`);
  },

  /**
   * Pobiera kolejkę odkryć (discovery queue)
   */
  getDiscoveryQueue: (limit = 12) => {
    return apiClient.get(`/v1/recommendations/discovery-queue?limit=${limit}`);
  },

  /**
   * Pobiera znanych autorów użytkownika
   */
  getKnownAuthors: (limit = 6) => {
    return apiClient.get(`/v1/recommendations/known-authors?limit=${limit}`);
  },

  /**
   * Pobiera podobne książki do danej książki
   */
  getSimilar: (bookId, limit = 8) => {
    return apiClient.get(`/v1/recommendations/similar/${bookId}?limit=${limit}`);
  },

  /**
   * Raportuje interakcję użytkownika (view, review, borrow, wishlist_add/remove)
   * WAŻNE: Używa UNIFIED endpoint - wszystkie interakcje idą do jednej kolekcji
   * 
   * @param {string} bookId - ID książki
   * @param {string} interactionType - 'view' | 'review' | 'borrow' | 'wishlist_add' | 'wishlist_remove'
   * @param {object} metadata - Dodatkowe dane (opcjonalne)
   */
  reportInteraction: (bookId, interactionType, metadata = {}) => {
    return apiClient.post('/v1/recommendations/interaction', {
      book_id: bookId,
      interaction_type: interactionType,
      metadata,
    });
  },

  /**
   * Pobiera metryki modelu LightGCN
   */
  getModelMetrics: () => {
    return apiClient.get('/v1/recommendations/metrics');
  },

  /**
   * Sprawdza status systemu rekomendacji
   */
  getHealth: () => {
    return apiClient.get('/v1/recommendations/health');
  },

  /**
   * 🆕 Porównuje metryki różnorodności dla różnych wartości lambda
   * Pomocne do eksperymentowania z optymalnym λ
   * 
   * @param {number} n - Liczba rekomendacji do porównania
   * @param {string} lambdaValues - Lista λ oddzielona przecinkami (np. "0.3,0.5,0.7,0.9")
   */
  getDiversityComparison: (n = 30, lambdaValues = '0.3,0.5,0.7,0.9') => {
    return apiClient.get('/v1/recommendations/diversity-comparison', {
      params: { n, lambda_values: lambdaValues },
    });
  },

  /**
   * 🆕 Pobiera statystyki embeddingów (debug)
   */
  getEmbeddingStats: () => {
    return apiClient.get('/v1/recommendations/embedding-stats');
  },

  /**
   * 🆕 Pobiera statystyki użytkownika (debug)
   * Admin może sprawdzić dowolnego użytkownika, zwykły user tylko siebie
   */
  getUserStats: (userId) => {
    return apiClient.get(`/v1/recommendations/debug/user-stats/${userId}`);
  },

  /**
   * 🆕 Pobiera statystyki serwisu (admin only)
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
    // Obsłuż zarówno string ID jak i cały obiekt książki
    const bookId = typeof bookIdOrObject === 'string' 
      ? bookIdOrObject 
      : bookIdOrObject._id || bookIdOrObject.id;
    
    return apiClient.post('/v1/loans/borrow', { book_id: String(bookId) });
  },

  /**
   * Alias dla borrow() - dla kompatybilności z BookDetails.jsx
   */
  create: (bookIdOrObject) => {
    // Obsłuż zarówno string ID jak i cały obiekt książki
    const bookId = typeof bookIdOrObject === 'string' 
      ? bookIdOrObject 
      : bookIdOrObject._id || bookIdOrObject.id;
    
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
   * ✅ Używa /loans/me (zgodnie z Twoim backendem)
   */
  getMine: (status = null) => {
    const params = status ? { status } : {};
    return apiClient.get('/v1/loans/me', { params });
  },

  /**
   * Pobierz wypożyczenia użytkownika (alias dla getMine)
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
   * @param {string} bookId - ID książki
   * @param {number} rating - Ocena (1-5)
   * @param {string} content - Treść recenzji (opcjonalna)
   */
  create: (bookId, rating, content = '') => {
    return apiClient.post('/v1/reviews', {
      book_id: String(bookId),
      rating: Number(rating),
      content: String(content),  // ← POPRAWKA: content zamiast comment
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
    // Używamy unified interaction endpoint
    return recommendationsAPI.reportInteraction(bookId, 'wishlist_add');
  },

  remove: (bookId) => {
    // Używamy unified interaction endpoint
    return recommendationsAPI.reportInteraction(bookId, 'wishlist_remove');
  },

  getAll: () => {
    return apiClient.get('/v1/wishlist');
  },
};

// ============================================================================
// STATS API (dla dashboardu admina)
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
// USERS API (profile, statistics)
// ============================================================================

export const usersAPI = {
  /**
   * Pobiera profil użytkownika (używa authAPI.getCurrentUser)
   */
  getMe: () => {
    return authAPI.getCurrentUser();
  },

  /**
   * Pobiera profil użytkownika (alias dla getMe)
   */
  getProfile: () => {
    return authAPI.getCurrentUser();
  },

  /**
   * Pobiera statystyki użytkownika (wypożyczenia, recenzje, interakcje)
   * UWAGA: Używa endpoint recommendations/embedding-stats jako fallback
   * Możesz stworzyć dedykowany endpoint /v1/users/me/stats jeśli potrzebujesz
   */
  getUserStats: async () => {
    try {
      // Próbuj użyć dedykowanego endpointu jeśli istnieje
      return await apiClient.get('/v1/users/me/stats');
    } catch (err) {
      // Fallback - użyj embedding stats z recommendations
      console.log('Using embedding-stats as fallback for user stats');
      return await recommendationsAPI.getEmbeddingStats();
    }
  },

  /**
   * Aktualizuje preferencje użytkownika
   */
  updatePreferences: (preferences) => {
    return apiClient.put('/v1/users/me/preferences', preferences);
  },

  /**
   * Pobiera historię aktywności użytkownika
   */
  getActivityHistory: (params = {}) => {
    return apiClient.get('/v1/users/me/activity', { params });
  },

  /**
   * Pobiera ulubione gatunki użytkownika (z interakcji)
   */
  getFavoriteGenres: () => {
    return apiClient.get('/v1/users/me/favorite-genres');
  },
};

export default apiClient;