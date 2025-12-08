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
  // Zwracamy dalej axios.Response – bez mocków i bez łapania błędów

  getFeatured: (limit = 10) => {
    return api.get('/recommendations/featured', {
      params: { limit },
    });
  },

  getCategories: () => {
    return api.get('/recommendations/categories');
  },

  getBecauseYouBorrowed: (limit = 3) => {
    return api.get('/recommendations/because-borrowed', {
      params: { limit },
    });
  },

  getDiscoveryQueue: (limit = 12) => {
    return api.get('/recommendations/discovery-queue', {
      params: { limit },
    });
  },

  getKnownAuthors: (limit = 6) => {
    return api.get('/recommendations/known-authors', {
      params: { limit },
    });
  },

  getModelMetrics: () => {
    return api.get('/recommendations/metrics');
  },

  getForUser: (userId, n = 20) => {
    return api.get(`/recommendations/user/${userId}`, {
      params: { n },
    });
  },

  getSimilar: (bookId, limit = 8) => {
    return api.get(`/recommendations/similar/${bookId}`, {
      params: { limit },
    });
  },


reportInteraction: (bookId, interactionType, metadata = {}) =>
  api.post('/recommendations/interaction', {
    book_id: bookId,
    interaction_type: interactionType,
    metadata,
  }),


  getHealth: () => {
    return api.get('/recommendations/health');
  },
};

export default recommendationsAPI;
