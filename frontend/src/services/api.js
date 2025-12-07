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
  // Pobierz wszystkie wypożyczenia (admin/librarian)
  getAll: (params = {}) => api.get('/loans/', { params }),
  
  // Pobierz moje wypożyczenia
  getMine: () => api.get('/loans/me'),
  
  // Pobierz szczegóły wypożyczenia
  getById: (id) => api.get(`/loans/${id}`),
  
  // Utwórz nowe wypożyczenie
  create: (data) => api.post('/loans/', data),
  
  // Zwróć książkę
  return: (id, data = {}) => api.post(`/loans/${id}/return`, data),
  
  // Przedłuż wypożyczenie
  renew: (id) => api.post(`/loans/${id}/renew`),
  
  // Sprawdź czy użytkownik może wypożyczyć daną książkę
  canBorrow: (bookId) => api.get(`/loans/can-borrow/${bookId}`)
};

// Reviews API
export const reviewsAPI = {
  // Pobierz recenzje dla książki
  getByBook: (bookId) => api.get(`/reviews/book/${bookId}`),
  
  // Pobierz moje recenzje
  getMine: () => api.get('/reviews/me'),
  
  // Dodaj recenzję
  create: (data) => api.post('/reviews/', data),
  
  // Zaktualizuj recenzję
  update: (id, data) => api.put(`/reviews/${id}`, data),
  
  // Usuń recenzję
  delete: (id) => api.delete(`/reviews/${id}`)
};

// Recommendations API (direct access to recommendation engine)
export const recommendationsAPI = {
  // Rekomendacje dla użytkownika goodbooks
  getForUser: (userId, n = 10) => 
    api.get(`/api/recommendations/user/${userId}`, { params: { n } }),
  
  // Podobne książki
  getSimilar: (bookId, n = 10) => 
    api.get(`/api/recommendations/similar/${bookId}`, { params: { n } }),
  
  // Health check
  health: () => api.get('/api/recommendations/health')
};

export default api;