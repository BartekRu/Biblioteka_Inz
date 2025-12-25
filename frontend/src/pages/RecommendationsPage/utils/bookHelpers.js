/**
 * bookHelpers.js - Utility functions for book data handling
 */

/**
 * Get book cover image with fallback
 */
export const getBookImage = (book) =>
  book?.coverImage || book?.image_url || book?.small_image_url || '/default-book-cover.jpg';

/**
 * Get book genres (handles different field names)
 */
export const getBookGenres = (book) => {
  if (Array.isArray(book?.genres)) return book.genres;
  if (typeof book?.genre === 'string') return [book.genre];
  if (Array.isArray(book?.genre)) return book.genre;
  return [];
};

/**
 * Get book rating
 */
export const getBookRating = (book) => book?.averageRating ?? book?.average_rating ?? 0;

/**
 * Get book review count
 */
export const getBookReviewCount = (book) =>
  book?.reviewCount ?? book?.total_reviews ?? book?.ratings_count ?? book?.reviews_count ?? 0;

/**
 * Check if book is available
 */
export const isBookAvailable = (book) => {
  if (typeof book?.available === 'boolean') return book.available;
  if (typeof book?.available_copies === 'number') {
    return book.available_copies > 0;
  }
  return true;
};

/**
 * Get availability text
 */
export const getAvailabilityText = (book) => {
  if (isBookAvailable(book)) return 'Dostępna';
  if (book?.available_copies === 0) return 'Wypożyczona';
  if (book?.reservations > 0) return `W kolejce: ${book.reservations}`;
  return 'Niedostępna';
};

/**
 * Get match score percentage
 */
export const getMatchScorePercent = (book) => {
  if (!book?.matchScore) return null;
  return Math.round(book.matchScore * 100);
};

/**
 * Truncate text to specified length
 */
export const truncateText = (text, maxLength = 150) => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
};

/**
 * Format recommendation reason
 */
export const getRecommendationReason = (book, defaultReason = 'Polecane przez AI') => {
  if (book?.recommendationReason) return book.recommendationReason;
  if (book?.recommendation_source) {
    const sourceMap = {
      lightgcn: 'Dopasowane do Twoich preferencji',
      similar_users: 'Lubiane przez podobnych czytelników',
      similar_books: 'Podobne do książek które lubisz',
      genre: 'Z Twojego ulubionego gatunku',
      author: 'Od autora którego znasz',
    };
    return sourceMap[book.recommendation_source] || defaultReason;
  }
  return defaultReason;
};

/**
 * Sort books by match score
 */
export const sortByMatchScore = (books) => {
  return [...books].sort((a, b) => (b.matchScore || 0) - (a.matchScore || 0));
};

/**
 * Group books by author
 */
export const groupByAuthor = (books) => {
  return books.reduce((acc, book) => {
    const author = book.author || 'Unknown';
    if (!acc[author]) acc[author] = [];
    acc[author].push(book);
    return acc;
  }, {});
};

/**
 * Group books by genre
 */
export const groupByGenre = (books) => {
  const grouped = {};
  books.forEach((book) => {
    const genres = getBookGenres(book);
    genres.forEach((genre) => {
      if (!grouped[genre]) grouped[genre] = [];
      grouped[genre].push(book);
    });
  });
  return grouped;
};

/**
 * Get top N items from array
 */
export const getTopN = (array, n = 5) => {
  return array.slice(0, n);
};

/**
 * Shuffle array (Fisher-Yates algorithm)
 */
export const shuffleArray = (array) => {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
};
