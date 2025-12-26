

import { useState, useEffect, useCallback } from 'react';
import { recommendationsAPI } from '../../../services/api';

export const useGenreRecommendations = (limit = 3, booksPerGenre = 10) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    console.log('🔄 Fetching genre recommendations...', { limit, booksPerGenre });
    setLoading(true);
    setError(null);

    try {
      const response = await recommendationsAPI.getByGenre(limit, booksPerGenre);
      
      console.log('✅ Genre recommendations response:', {
        type: typeof response,
        isArray: Array.isArray(response),
        length: response?.length,
        data: response,
      });

      // Validate response
      if (!response) {
        throw new Error('Empty response from API');
      }

      if (!Array.isArray(response)) {
        console.warn('⚠️ Response is not an array, wrapping...', response);
        setData([response]);
      } else {
        setData(response);
      }
    } catch (err) {
      console.error('❌ Failed to fetch genre recommendations:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
      });
      
      setError(err);
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [limit, booksPerGenre]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    genreSections: data,
    loading,
    error,
    refresh: fetchData,
  };
};

/**
 * Hook do pobierania rekomendacji od podobnych czytelników
 */
export const useSimilarReadersRecommendations = (limit = 15) => {
  const [data, setData] = useState({ books: [], similar_user_count: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    console.log('🔄 Fetching similar readers recommendations...', { limit });
    setLoading(true);
    setError(null);

    try {
      const response = await recommendationsAPI.getSimilarReaders(limit);
      
      console.log('✅ Similar readers response:', {
        type: typeof response,
        hasBooks: !!response?.books,
        booksCount: response?.books?.length,
        similarUserCount: response?.similar_user_count,
        data: response,
      });

      // Validate response
      if (!response) {
        throw new Error('Empty response from API');
      }

      if (!response.books) {
        console.warn('⚠️ Response missing books array');
        setData({ books: [], similar_user_count: 0, metadata: response.metadata });
      } else {
        setData(response);
      }
    } catch (err) {
      console.error('❌ Failed to fetch similar readers recommendations:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
      });
      
      setError(err);
      setData({ books: [], similar_user_count: 0 });
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    books: data.books,
    similarUserCount: data.similar_user_count,
    metadata: data.metadata,
    loading,
    error,
    refresh: fetchData,
  };
};

/**
 * Hook do pobierania rekomendacji według autora
 */
export const useAuthorRecommendations = (limit = 3, booksPerAuthor = 10) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    console.log('🔄 Fetching author recommendations...', { limit, booksPerAuthor });
    setLoading(true);
    setError(null);

    try {
      const response = await recommendationsAPI.getByAuthor(limit, booksPerAuthor);
      
      console.log('✅ Author recommendations response:', {
        type: typeof response,
        isArray: Array.isArray(response),
        length: response?.length,
        data: response,
      });

      if (!Array.isArray(response)) {
        console.warn('⚠️ Response is not an array, wrapping...', response);
        setData([response]);
      } else {
        setData(response);
      }
    } catch (err) {
      console.error('❌ Failed to fetch author recommendations:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
      });
      
      setError(err);
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [limit, booksPerAuthor]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    authorSections: data,
    loading,
    error,
    refresh: fetchData,
  };
};

/**
 * Debug helper - sprawdź czy API odpowiada
 */
export const useAPIHealthCheck = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      console.log('🏥 Checking API health...');
      
      try {
        const response = await recommendationsAPI.getHealth();
        console.log('✅ API Health:', response);
        setStatus(response);
      } catch (err) {
        console.error('❌ API Health check failed:', err);
        setStatus({ status: 'error', error: err.message });
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
  }, []);

  return { status, loading };
};