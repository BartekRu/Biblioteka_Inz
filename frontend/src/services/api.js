import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add token to requests if it exists
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle 401 errors (token expired)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      // Optionally redirect to login
      // window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Books API
export const booksAPI = {
  getAll: (params = {}) => api.get('/books/', { params }),
  getById: (id) => api.get(`/books/${id}`),
  create: (data) => api.post('/books/', data),
  update: (id, data) => api.put(`/books/${id}`, data),
  delete: (id) => api.delete(`/books/${id}`),
  search: (query) => api.get('/books/', { params: { search: query } })
};

// Auth API
export const authAPI = {
  login: (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    return api.post('/auth/token', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
  },
  register: (data) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me')
};

// Users API
export const usersAPI = {
  getMe: () => api.get('/users/me'),
  updateMe: (data) => api.patch('/users/me', data),
  getRecommendations: (params) => api.get('/users/me/recommendations', { params }),
  setPreferences: (data) => api.post('/users/me/preferences', data)
};

// Loans API
export const loansAPI = {
  getAll: (params = {}) => api.get('/loans/', { params }),
  getMine: () => api.get('/loans/me'),
  getById: (id) => api.get(`/loans/${id}`),
  create: (data) => api.post('/loans/', data),
  return: (id, data = {}) => api.post(`/loans/${id}/return`, data),
  renew: (id) => api.post(`/loans/${id}/renew`),
  canBorrow: (bookId) => api.get(`/loans/can-borrow/${bookId}`)
};

// Reviews API
export const reviewsAPI = {
  getByBook: (bookId) => api.get(`/reviews/book/${bookId}`),
  getMine: () => api.get('/reviews/me'),
  create: (data) => api.post('/reviews/', data),
  update: (id, data) => api.put(`/reviews/${id}`, data),
  delete: (id) => api.delete(`/reviews/${id}`)
};

// ============================================================================
// RECOMMENDATIONS API - dla strony rekomendacji
// ============================================================================
export const recommendationsAPI = {
  // Wyróżnione rekomendacje (carousel)
  getFeatured: (limit = 10) => 
    api.get('/recommendations/featured', { params: { limit } }),

  // Kategorie z okładkami
  getCategories: () => 
    api.get('/recommendations/categories'),

  // Sekcje "Ponieważ wypożyczyłeś"
  getBecauseYouBorrowed: (limit = 3) => 
    api.get('/recommendations/because-borrowed', { params: { limit } }),

  // Kolejka odkryć
  getDiscoveryQueue: (limit = 12) => 
    api.get('/recommendations/discovery-queue', { params: { limit } }),

  // Znani autorzy
  getKnownAuthors: (limit = 6) => 
    api.get('/recommendations/known-authors', { params: { limit } }),

  // Metryki modelu
  getModelMetrics: () => 
    api.get('/recommendations/metrics'),

  // Podobne książki
  getSimilar: (bookId, limit = 8) => 
    api.get(`/recommendations/similar/${bookId}`, { params: { limit } }),

  // Raportuj interakcję
  reportInteraction: (bookId, interactionType, metadata = {}) => 
    api.post('/recommendations/interaction', null, {
      params: {
        book_id: bookId,
        interaction_type: interactionType
      },
      data: metadata
    }),

  // Health check
  getHealth: () => 
    api.get('/recommendations/health')
};

export default api;