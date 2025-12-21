/**
 * hooks/useInteractions.js
 * React Hooks for managing interactions: view, borrow, review
 */
import { useState } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000/v1';

// ============ REVIEWS ============

export const useReviews = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const addReview = async (bookId, rating, content) => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');
      
      const response = await axios.post(
        `${API_URL}/reviews`,
        { book_id: bookId, rating, content },
        { headers: { 'Authorization': `Bearer ${token}` } }
      );

      console.log('✅ Review created:', response.data);
      console.log('✅ Interaction weight: 0.8 (review)');
      console.log('✅ Embedding updated:', response.data.embedding_updated);

      return response.data;
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Error creating review');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const getBookReviews = async (bookId) => {
    try {
      const response = await axios.get(`${API_URL}/reviews/${bookId}`);
      return response.data;
    } catch (err) {
      setError(err.response?.data?.detail || 'Error fetching reviews');
      throw err;
    }
  };

  return { addReview, getBookReviews, loading, error };
};

// ============ LOANS ============

export const useLoans = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const borrowBook = async (bookId) => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');
      
      const response = await axios.post(
        `${API_URL}/loans/borrow`,
        { book_id: bookId },
        { headers: { 'Authorization': `Bearer ${token}` } }
      );

      console.log('✅ Book borrowed:', response.data);
      console.log('✅ Interaction weight: 1.0 (borrow - strongest signal!)');
      console.log('✅ Embedding updated:', response.data.embedding_updated);

      return response.data;
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Error borrowing book');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const returnBook = async (loanId) => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');
      
      await axios.post(
        `${API_URL}/loans/return/${loanId}`,
        {},
        { headers: { 'Authorization': `Bearer ${token}` } }
      );

      console.log('✅ Book returned');
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Error returning book');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const getMyLoans = async (status = null) => {
    try {
      const token = localStorage.getItem('token');
      
      const url = status 
        ? `${API_URL}/loans/my-loans?status=${status}`
        : `${API_URL}/loans/my-loans`;
      
      const response = await axios.get(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      return response.data;
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Error fetching loans');
      throw err;
    }
  };

  return { borrowBook, returnBook, getMyLoans, loading, error };
};

// ============ VIEWS ============

export const useViews = () => {
  /**
   * Rejestruje wyświetlenie książki (waga 0.3)
   * Wywołaj w useEffect gdy user otwiera BookDetails
   */
  const registerView = async (bookId) => {
    try {
      const token = localStorage.getItem('token');
      
      await axios.post(
        `${API_URL}/views/view/${bookId}`,
        {},
        { headers: { 'Authorization': `Bearer ${token}` } }
      );

      console.log('✅ View registered (weight: 0.3)');
      
    } catch (err) {
      // Nie blokuj UI - to nie jest krytyczny błąd
      console.warn('⚠️ Failed to register view:', err);
    }
  };

  const getRecentlyViewed = async (limit = 20) => {
    try {
      const token = localStorage.getItem('token');
      
      const response = await axios.get(
        `${API_URL}/views/recent-views?limit=${limit}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      return response.data;
      
    } catch (err) {
      console.error('❌ Error fetching recent views:', err);
      return [];
    }
  };

  return { registerView, getRecentlyViewed };
};