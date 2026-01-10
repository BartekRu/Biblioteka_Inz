import { useState, useEffect, useCallback } from 'react';
import { recommendationsAPI } from '../../../services/api';

export const useGenreRecommendations = (limit = 3, booksPerGenre = 10) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await recommendationsAPI.getByGenre(limit, booksPerGenre);

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

export const useSimilarReadersRecommendations = (limit = 15) => {
  const [data, setData] = useState({ books: [], similar_user_count: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await recommendationsAPI.getSimilarReaders(limit);

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

export const useAuthorRecommendations = (limit = 3, booksPerAuthor = 10) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await recommendationsAPI.getByAuthor(limit, booksPerAuthor);

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

export const useAPIHealthCheck = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await recommendationsAPI.getHealth();
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
