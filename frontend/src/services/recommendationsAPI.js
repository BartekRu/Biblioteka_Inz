
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

  getFeatured: async (limit = 10) => {
    try {
      const response = await api.get('/recommendations/featured', {
        params: { limit }
      });
      return response;
    } catch (error) {
      console.error('Error fetching featured recommendations:', error);
      return { data: getMockFeaturedBooks() };
    }
  },


  getCategories: async () => {
    try {
      const response = await api.get('/recommendations/categories');
      return response;
    } catch (error) {
      console.error('Error fetching categories:', error);
      return { data: getMockCategories() };
    }
  },


  getBecauseYouBorrowed: async (limit = 3) => {
    try {
      const response = await api.get('/recommendations/because-borrowed', {
        params: { limit }
      });
      return response;
    } catch (error) {
      console.error('Error fetching because-borrowed recommendations:', error);
      return { data: getMockBecauseSections() };
    }
  },


  getDiscoveryQueue: async (limit = 12) => {
    try {
      const response = await api.get('/recommendations/discovery-queue', {
        params: { limit }
      });
      return response;
    } catch (error) {
      console.error('Error fetching discovery queue:', error);
      return { data: getMockDiscoveryQueue() };
    }
  },


  getKnownAuthors: async (limit = 6) => {
    try {
      const response = await api.get('/recommendations/known-authors', {
        params: { limit }
      });
      return response;
    } catch (error) {
      console.error('Error fetching known authors:', error);
      return { data: getMockKnownAuthors() };
    }
  },


  getModelMetrics: async () => {
    try {
      const response = await api.get('/recommendations/metrics');
      return response;
    } catch (error) {
      console.error('Error fetching model metrics:', error);
      return { data: getMockModelMetrics() };
    }
  },


  getForUser: async (userId, n = 20) => {
    try {
      const response = await api.get(`/recommendations/user/${userId}`, {
        params: { n }
      });
      return response;
    } catch (error) {
      console.error('Error fetching user recommendations:', error);
      throw error;
    }
  },


  getSimilar: async (bookId, limit = 8) => {
    try {
      const response = await api.get(`/recommendations/similar/${bookId}`, {
        params: { limit }
      });
      return response;
    } catch (error) {
      console.error('Error fetching similar books:', error);
      throw error;
    }
  },


  reportInteraction: async (bookId, interactionType, metadata = {}) => {
    try {
      const response = await api.post('/recommendations/interaction', {
        book_id: bookId,
        interaction_type: interactionType,
        metadata
      });
      return response;
    } catch (error) {
      console.error('Error reporting interaction:', error);
    }
  },


  getHealth: async () => {
    try {
      const response = await api.get('/recommendations/health');
      return response;
    } catch (error) {
      console.error('Error checking recommendations health:', error);
      return { data: { status: 'unknown' } };
    }
  }
};


function getMockFeaturedBooks() {
  return [
    {
      _id: '1',
      title: 'Władca Pierścieni: Drużyna Pierścienia',
      author: 'J.R.R. Tolkien',
      coverImage: 'https://covers.openlibrary.org/b/id/8406786-L.jpg',
      description: 'Epicka opowieść o hobbicie Frodo Baggins, który musi zniszczyć potężny pierścień, zanim wpadnie w ręce Ciemnego Władcy Saurona.',
      genres: ['Fantasy', 'Przygodowe', 'Klasyka'],
      averageRating: 4.8,
      reviewCount: 1250,
      available: true,
      matchScore: 0.95,
      recommendationReason: 'Podobne do książek które uwielbiasz',
      onWishlist: true
    },
    {
      _id: '2',
      title: 'Dune',
      author: 'Frank Herbert',
      coverImage: 'https://covers.openlibrary.org/b/id/8091016-L.jpg',
      description: 'Na pustynnej planecie Arrakis rozgrywa się epicka saga o polityce, religii i ekologii.',
      genres: ['Sci-Fi', 'Polityczne', 'Ekologiczne'],
      averageRating: 4.7,
      reviewCount: 980,
      available: true,
      matchScore: 0.92,
      recommendationReason: 'Bestseller w Twoim ulubionym gatunku'
    },
    {
      _id: '3',
      title: 'Zbrodnia i kara',
      author: 'Fiodor Dostojewski',
      coverImage: 'https://covers.openlibrary.org/b/id/10498471-L.jpg',
      description: 'Psychologiczny thriller o studencie Raskolnikowie i jego walce z wyrzutami sumienia.',
      genres: ['Klasyka', 'Psychologiczne', 'Literatura rosyjska'],
      averageRating: 4.5,
      reviewCount: 756,
      available: false,
      matchScore: 0.88,
      recommendationReason: 'Użytkownicy o podobnych gustach polecają'
    }
  ];
}

function getMockCategories() {
  return [
    {
      name: 'Fantasy',
      count: 1250,
      sampleCovers: [
        'https://covers.openlibrary.org/b/id/8406786-M.jpg',
        'https://covers.openlibrary.org/b/id/8091016-M.jpg',
        'https://covers.openlibrary.org/b/id/10498471-M.jpg',
        'https://covers.openlibrary.org/b/id/7884873-M.jpg',
        'https://covers.openlibrary.org/b/id/6979861-M.jpg',
        'https://covers.openlibrary.org/b/id/8314139-M.jpg'
      ]
    },
    {
      name: 'Kryminał',
      count: 890,
      sampleCovers: [
        'https://covers.openlibrary.org/b/id/8314139-M.jpg',
        'https://covers.openlibrary.org/b/id/7884873-M.jpg',
        'https://covers.openlibrary.org/b/id/6979861-M.jpg',
        'https://covers.openlibrary.org/b/id/8091016-M.jpg',
        'https://covers.openlibrary.org/b/id/10498471-M.jpg',
        'https://covers.openlibrary.org/b/id/8406786-M.jpg'
      ]
    },
    {
      name: 'Sci-Fi',
      count: 720,
      sampleCovers: [
        'https://covers.openlibrary.org/b/id/8091016-M.jpg',
        'https://covers.openlibrary.org/b/id/8314139-M.jpg',
        'https://covers.openlibrary.org/b/id/7884873-M.jpg',
        'https://covers.openlibrary.org/b/id/6979861-M.jpg',
        'https://covers.openlibrary.org/b/id/10498471-M.jpg',
        'https://covers.openlibrary.org/b/id/8406786-M.jpg'
      ]
    },
    {
      name: 'Romans',
      count: 1100,
      sampleCovers: [
        'https://covers.openlibrary.org/b/id/7884873-M.jpg',
        'https://covers.openlibrary.org/b/id/8091016-M.jpg',
        'https://covers.openlibrary.org/b/id/8314139-M.jpg',
        'https://covers.openlibrary.org/b/id/6979861-M.jpg',
        'https://covers.openlibrary.org/b/id/10498471-M.jpg',
        'https://covers.openlibrary.org/b/id/8406786-M.jpg'
      ]
    },
    {
      name: 'Horror',
      count: 450,
      sampleCovers: [
        'https://covers.openlibrary.org/b/id/6979861-M.jpg',
        'https://covers.openlibrary.org/b/id/8091016-M.jpg',
        'https://covers.openlibrary.org/b/id/8314139-M.jpg',
        'https://covers.openlibrary.org/b/id/7884873-M.jpg',
        'https://covers.openlibrary.org/b/id/10498471-M.jpg',
        'https://covers.openlibrary.org/b/id/8406786-M.jpg'
      ]
    },
    {
      name: 'Literatura piękna',
      count: 680,
      sampleCovers: [
        'https://covers.openlibrary.org/b/id/10498471-M.jpg',
        'https://covers.openlibrary.org/b/id/8091016-M.jpg',
        'https://covers.openlibrary.org/b/id/8314139-M.jpg',
        'https://covers.openlibrary.org/b/id/7884873-M.jpg',
        'https://covers.openlibrary.org/b/id/6979861-M.jpg',
        'https://covers.openlibrary.org/b/id/8406786-M.jpg'
      ]
    }
  ];
}

function getMockBecauseSections() {
  return [
    {
      sourceBook: {
        _id: 'source1',
        title: 'Harry Potter i Kamień Filozoficzny',
        author: 'J.K. Rowling'
      },
      recommendations: [
        {
          _id: 'rec1',
          title: 'Opowieści z Narnii',
          author: 'C.S. Lewis',
          coverImage: 'https://covers.openlibrary.org/b/id/8314139-L.jpg',
          genres: ['Fantasy', 'Dla młodzieży'],
          averageRating: 4.5,
          reviewCount: 890,
          available: true,
          matchScore: 0.89
        },
        {
          _id: 'rec2',
          title: 'Eragon',
          author: 'Christopher Paolini',
          coverImage: 'https://covers.openlibrary.org/b/id/7884873-L.jpg',
          genres: ['Fantasy', 'Smoki'],
          averageRating: 4.3,
          reviewCount: 654,
          available: true,
          matchScore: 0.85
        },
        {
          _id: 'rec3',
          title: 'Percy Jackson',
          author: 'Rick Riordan',
          coverImage: 'https://covers.openlibrary.org/b/id/6979861-L.jpg',
          genres: ['Fantasy', 'Mitologia'],
          averageRating: 4.6,
          reviewCount: 1120,
          available: false,
          matchScore: 0.87
        },
        {
          _id: 'rec4',
          title: 'Artemis Fowl',
          author: 'Eoin Colfer',
          coverImage: 'https://covers.openlibrary.org/b/id/8091016-L.jpg',
          genres: ['Fantasy', 'Przygodowe'],
          averageRating: 4.2,
          reviewCount: 445,
          available: true,
          matchScore: 0.82
        }
      ]
    },
    {
      sourceBook: {
        _id: 'source2',
        title: '1984',
        author: 'George Orwell'
      },
      recommendations: [
        {
          _id: 'rec5',
          title: 'Nowy wspaniały świat',
          author: 'Aldous Huxley',
          coverImage: 'https://covers.openlibrary.org/b/id/10498471-L.jpg',
          genres: ['Dystopia', 'Sci-Fi'],
          averageRating: 4.4,
          reviewCount: 780,
          available: true,
          matchScore: 0.91
        },
        {
          _id: 'rec6',
          title: 'Fahrenheit 451',
          author: 'Ray Bradbury',
          coverImage: 'https://covers.openlibrary.org/b/id/8406786-L.jpg',
          genres: ['Dystopia', 'Klasyka'],
          averageRating: 4.3,
          reviewCount: 650,
          available: true,
          matchScore: 0.88
        },
        {
          _id: 'rec7',
          title: 'Rok 1984 i inne utwory',
          author: 'George Orwell',
          coverImage: 'https://covers.openlibrary.org/b/id/8314139-L.jpg',
          genres: ['Klasyka', 'Polityczne'],
          averageRating: 4.5,
          reviewCount: 320,
          available: true,
          matchScore: 0.86
        }
      ]
    }
  ];
}

function getMockDiscoveryQueue() {
  return [
    {
      _id: 'dq1',
      title: 'Mistrz i Małgorzata',
      author: 'Michaił Bułhakow',
      coverImage: 'https://covers.openlibrary.org/b/id/8406786-L.jpg',
      available: true
    },
    {
      _id: 'dq2',
      title: 'Solaris',
      author: 'Stanisław Lem',
      coverImage: 'https://covers.openlibrary.org/b/id/8091016-L.jpg',
      available: true
    },
    {
      _id: 'dq3',
      title: 'Wiedźmin: Ostatnie życzenie',
      author: 'Andrzej Sapkowski',
      coverImage: 'https://covers.openlibrary.org/b/id/8314139-L.jpg',
      available: false
    },
    {
      _id: 'dq4',
      title: 'Ferdydurke',
      author: 'Witold Gombrowicz',
      coverImage: 'https://covers.openlibrary.org/b/id/7884873-L.jpg',
      available: true
    },
    {
      _id: 'dq5',
      title: 'Lalka',
      author: 'Bolesław Prus',
      coverImage: 'https://covers.openlibrary.org/b/id/6979861-L.jpg',
      available: true
    },
    {
      _id: 'dq6',
      title: 'Quo Vadis',
      author: 'Henryk Sienkiewicz',
      coverImage: 'https://covers.openlibrary.org/b/id/10498471-L.jpg',
      available: true
    }
  ];
}

function getMockKnownAuthors() {
  return [
    {
      name: 'J.K. Rowling',
      latestBook: {
        title: 'Harry Potter i Insygnia Śmierci',
        coverImage: 'https://covers.openlibrary.org/b/id/8314139-L.jpg',
        available: true
      }
    },
    {
      name: 'Stephen King',
      latestBook: {
        title: 'To',
        coverImage: 'https://covers.openlibrary.org/b/id/8091016-L.jpg',
        available: false
      }
    },
    {
      name: 'Andrzej Sapkowski',
      latestBook: {
        title: 'Sezon burz',
        coverImage: 'https://covers.openlibrary.org/b/id/7884873-L.jpg',
        available: true
      }
    },
    {
      name: 'Brandon Sanderson',
      latestBook: {
        title: 'Droga Królów',
        coverImage: 'https://covers.openlibrary.org/b/id/6979861-L.jpg',
        available: true
      }
    }
  ];
}

function getMockModelMetrics() {
  return {
    recall20: 0.1411,
    ndcg20: 0.0842,
    precision20: 0.0623,
    coverage: 0.78,
    trainUsers: '35,710',
    trainItems: '10,000',
    interactions: '932,940',
    embeddingDim: '64',
    epochs: '50',
    learningRate: '0.001',
    lastUpdated: new Date().toLocaleDateString('pl-PL'),
    modelName: 'LightGCN',
    layers: 3
  };
}

export default recommendationsAPI;