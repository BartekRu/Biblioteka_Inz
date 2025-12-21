import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const recommendationsAPI = {
  getFeatured: (limit = 10) => api.get('/recommendations/featured', { params: { limit } }),

  getCategories: () => api.get('/recommendations/categories'),

  getBecauseYouBorrowed: (limit = 3) =>
    api.get('/recommendations/because-borrowed', { params: { limit } }),

  getDiscoveryQueue: (limit = 12) =>
    api.get('/recommendations/discovery-queue', { params: { limit } }),

  getKnownAuthors: (limit = 6) => api.get('/recommendations/known-authors', { params: { limit } }),

  getModelMetrics: () => api.get('/recommendations/metrics'),

  // 🔐 rekomendacje dla aktualnego użytkownika
  getForMe: (limit = 20) => api.get('/recommendations/user', { params: { limit } }),

  getSimilar: (bookId, limit = 8) =>
    api.get(`/recommendations/similar/${bookId}`, { params: { limit } }),

  // 🧠 delegacja do InteractionService
  reportInteraction: (bookId, interactionType, metadata = {}) =>
    api.post('/recommendations/interaction', {
      book_id: bookId,
      interaction_type: interactionType,
      metadata,
    }),

  getHealth: () => api.get('/recommendations/health'),
};

export default recommendationsAPI;
