import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Button,
  Chip,
  Rating,
  Divider,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  TextField,
  Avatar,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar
} from '@mui/material';
import {
  ArrowBack,
  MenuBook,
  Person,
  CalendarMonth,
  Category,
  Language,
  LocalLibrary,
  Star,
  Send,
  Delete
} from '@mui/icons-material';
// Poprawione ścieżki importów dla lokalizacji pages/BookCatalog/
import { booksAPI, loansAPI, reviewsAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import recommendationsAPI from '../../services/recommendationsAPI';

const BookDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();

  // Stan książki
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Stan wypożyczenia
  const [borrowing, setBorrowing] = useState(false);
  const [borrowDialog, setBorrowDialog] = useState(false);
  const [borrowSuccess, setBorrowSuccess] = useState(false);

  // Stan recenzji
  const [reviews, setReviews] = useState([]);
  const [reviewsLoading, setReviewsLoading] = useState(true);
  const [newReview, setNewReview] = useState({ rating: 0, content: '' });
  const [submittingReview, setSubmittingReview] = useState(false);

  // Snackbar
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });


  useEffect(() => {
  if (book?._id) {
    recommendationsAPI.reportInteraction(book._id, "view");
  }
}, [book?._id]);

  // Pobierz dane książki
  useEffect(() => {
    const fetchBook = async () => {
      try {
        setLoading(true);
        const response = await booksAPI.getById(id);
        setBook(response.data);
      } catch (err) {
        console.error('Error fetching book:', err);
        setError('Nie udało się pobrać danych książki');
      } finally {
        setLoading(false);
      }
    };

    fetchBook();
  }, [id]);

  // Pobierz recenzje
  useEffect(() => {
    const fetchReviews = async () => {
      try {
        setReviewsLoading(true);
        const response = await reviewsAPI.getByBook(id);
        setReviews(response.data);
      } catch (err) {
        console.error('Error fetching reviews:', err);
        // Nie pokazuj błędu - po prostu pusta lista
      } finally {
        setReviewsLoading(false);
      }
    };

    if (id) fetchReviews();
  }, [id]);

  // Wypożycz książkę
  const handleBorrow = async () => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: `/books/${id}` } });
      return;
    }

    try {
      setBorrowing(true);
await recommendationsAPI.reportInteraction(book, "borrow");
      
      // Odśwież dane książki
      const response = await booksAPI.getById(id);
      setBook(response.data);
      
      setBorrowDialog(false);
      setBorrowSuccess(true);
      setSnackbar({
        open: true,
        message: 'Książka została wypożyczona! Termin zwrotu: 30 dni.',
        severity: 'success'
      });
    } catch (err) {
  console.error(err);
  const detail = err.response?.data?.detail;

  if (Array.isArray(detail)) {
    setError(detail.map(d => d.msg).join(', '));
  } else if (typeof detail === 'string') {
    setError(detail);
  } else {
    setError('Nie udało się wypożyczyć książki.');
  }


    } finally {
      setBorrowing(false);
    }
  };

  // Dodaj recenzję
  const handleSubmitReview = async (e) => {
    e.preventDefault();
    
    if (!isAuthenticated) {
      navigate('/login', { state: { from: `/books/${id}` } });
      return;
    }

    if (newReview.rating === 0) {
      setSnackbar({
        open: true,
        message: 'Wybierz ocenę (1-5 gwiazdek)',
        severity: 'warning'
      });
      return;
    }

    try {
      setSubmittingReview(true);
      const response = await reviewsAPI.create({
        book_id: id,
        rating: newReview.rating,
        content: newReview.content
      });
      
      setReviews([response.data, ...reviews]);
      setNewReview({ rating: 0, content: '' });
      setSnackbar({
        open: true,
        message: 'Recenzja została dodana!',
        severity: 'success'
      });
      
      // Odśwież książkę (średnia ocen mogła się zmienić)
      const bookResponse = await booksAPI.getById(id);
      setBook(bookResponse.data);
    } catch (err) {
      console.error('Error submitting review:', err);
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Nie udało się dodać recenzji',
        severity: 'error'
      });
    } finally {
      setSubmittingReview(false);
    }
  };

  // Usuń recenzję
  const handleDeleteReview = async (reviewId) => {
    try {
      await reviewsAPI.delete(reviewId);
      setReviews(reviews.filter(r => r._id !== reviewId));
      setSnackbar({
        open: true,
        message: 'Recenzja została usunięta',
        severity: 'success'
      });
    } catch (err) {
      console.error('Error deleting review:', err);
      setSnackbar({
        open: true,
        message: 'Nie udało się usunąć recenzji',
        severity: 'error'
      });
    }
  };

  // Placeholder image
  const getBookImage = () => {
    if (book?.image_url) return book.image_url;
    if (book?.cover_image) return book.cover_image;
    return null;
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !book) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error">{error || 'Książka nie została znaleziona'}</Alert>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/books')} sx={{ mt: 2 }}>
          Powrót do katalogu
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* Przycisk powrotu */}
      <Button
        startIcon={<ArrowBack />}
        onClick={() => navigate('/books')}
        sx={{ mb: 3 }}
      >
        Powrót do katalogu
      </Button>

      <Grid container spacing={4}>
        {/* Lewa kolumna - okładka */}
        <Grid item xs={12} md={4}>
          <Paper
            elevation={3}
            sx={{
              height: 450,
              backgroundImage: getBookImage()
                ? `url(${getBookImage()})`
                : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              backgroundSize: 'cover',
              backgroundPosition: 'center',
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            {!getBookImage() && (
              <MenuBook sx={{ fontSize: 100, color: 'rgba(255,255,255,0.5)' }} />
            )}
          </Paper>

          {/* Przycisk wypożyczenia */}
          <Box sx={{ mt: 2 }}>
            <Button
              variant="contained"
              size="large"
              fullWidth
              startIcon={<LocalLibrary />}
              disabled={book.available_copies === 0 || borrowSuccess}
              onClick={() => setBorrowDialog(true)}
              color={borrowSuccess ? 'success' : 'primary'}
            >
              {borrowSuccess
                ? 'Wypożyczona!'
                : book.available_copies > 0
                  ? `Wypożycz (${book.available_copies} dostępnych)`
                  : 'Brak dostępnych egzemplarzy'
              }
            </Button>
          </Box>
        </Grid>

        {/* Prawa kolumna - szczegóły */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            {/* Tytuł */}
            <Typography variant="h4" component="h1" gutterBottom>
              {book.title}
            </Typography>

            {/* Autor */}
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Person sx={{ mr: 1, color: 'text.secondary' }} />
              <Typography variant="h6" color="text.secondary">
                {book.authors_full || book.author}
              </Typography>
            </Box>

            {/* Rating */}
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <Rating value={book.average_rating || 0} precision={0.1} readOnly />
              <Typography variant="body1" sx={{ ml: 1 }}>
                {(book.average_rating || 0).toFixed(2)}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                ({(book.ratings_count || 0).toLocaleString()} ocen)
              </Typography>
            </Box>

            {/* Gatunki */}
            <Box sx={{ mb: 3 }}>
              {(book.genre || []).map((genre, index) => (
                <Chip
                  key={index}
                  label={genre}
                  sx={{ mr: 1, mb: 1 }}
                  color="primary"
                  variant="outlined"
                />
              ))}
            </Box>

            <Divider sx={{ my: 2 }} />

            {/* Szczegóły */}
            <Grid container spacing={2}>
              {book.publication_year && (
                <Grid item xs={6} sm={4}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <CalendarMonth sx={{ mr: 1, color: 'text.secondary' }} />
                    <Box>
                      <Typography variant="caption" color="text.secondary">Rok wydania</Typography>
                      <Typography variant="body2">{book.publication_year}</Typography>
                    </Box>
                  </Box>
                </Grid>
              )}

              {book.language && (
                <Grid item xs={6} sm={4}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Language sx={{ mr: 1, color: 'text.secondary' }} />
                    <Box>
                      <Typography variant="caption" color="text.secondary">Język</Typography>
                      <Typography variant="body2">
                        {book.language === 'en' ? 'Angielski' : book.language === 'pl' ? 'Polski' : book.language}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
              )}

              {book.pages && (
                <Grid item xs={6} sm={4}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <MenuBook sx={{ mr: 1, color: 'text.secondary' }} />
                    <Box>
                      <Typography variant="caption" color="text.secondary">Strony</Typography>
                      <Typography variant="body2">{book.pages}</Typography>
                    </Box>
                  </Box>
                </Grid>
              )}

              {book.isbn && (
                <Grid item xs={6} sm={4}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">ISBN</Typography>
                    <Typography variant="body2">{book.isbn}</Typography>
                  </Box>
                </Grid>
              )}

              {book.publisher && (
                <Grid item xs={6} sm={4}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Wydawca</Typography>
                    <Typography variant="body2">{book.publisher}</Typography>
                  </Box>
                </Grid>
              )}

              {book.location && (
                <Grid item xs={6} sm={4}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Lokalizacja</Typography>
                    <Typography variant="body2">{book.location}</Typography>
                  </Box>
                </Grid>
              )}
            </Grid>

            {/* Opis */}
            {book.description && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="h6" gutterBottom>Opis</Typography>
                <Typography variant="body1" color="text.secondary" sx={{ whiteSpace: 'pre-line' }}>
                  {book.description}
                </Typography>
              </>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Sekcja recenzji */}
      <Paper sx={{ p: 3, mt: 4 }}>
        <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
          <Star sx={{ mr: 1 }} />
          Recenzje ({reviews.length})
        </Typography>

        {/* Formularz nowej recenzji */}
        {isAuthenticated && (
          <Card sx={{ mb: 3, bgcolor: 'grey.50' }}>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Dodaj swoją recenzję
              </Typography>
              <Box component="form" onSubmit={handleSubmitReview}>
                <Box sx={{ mb: 2 }}>
                  <Typography component="legend" variant="body2">Twoja ocena:</Typography>
                  <Rating
                    value={newReview.rating}
                    onChange={(e, value) => setNewReview({ ...newReview, rating: value })}
                    size="large"
                  />
                </Box>
                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  placeholder="Napisz swoją opinię o książce... (opcjonalnie)"
                  value={newReview.content}
                  onChange={(e) => setNewReview({ ...newReview, content: e.target.value })}
                  sx={{ mb: 2 }}
                />
                <Button
                  type="submit"
                  variant="contained"
                  startIcon={<Send />}
                  disabled={submittingReview || newReview.rating === 0}
                >
                  {submittingReview ? 'Wysyłanie...' : 'Dodaj recenzję'}
                </Button>
              </Box>
            </CardContent>
          </Card>
        )}

        {!isAuthenticated && (
          <Alert severity="info" sx={{ mb: 3 }}>
            <Button color="inherit" onClick={() => navigate('/login')}>
              Zaloguj się
            </Button>
            , aby dodać recenzję
          </Alert>
        )}

        {/* Lista recenzji */}
        {reviewsLoading ? (
          <CircularProgress />
        ) : reviews.length === 0 ? (
          <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
            Brak recenzji. Bądź pierwszy i dodaj swoją opinię!
          </Typography>
        ) : (
          <Box>
            {reviews.map((review) => (
              <Card key={review._id} sx={{ mb: 2 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Avatar sx={{ mr: 2, bgcolor: 'primary.main' }}>
                        {(review.username || review.user_name || 'U')[0].toUpperCase()}
                      </Avatar>
                      <Box>
                        <Typography variant="subtitle2">
                          {review.username || review.user_name || 'Użytkownik'}
                        </Typography>
                        <Rating value={review.rating} size="small" readOnly />
                      </Box>
                    </Box>
                    
                    {/* Przycisk usunięcia (jeśli to recenzja użytkownika) */}
                    {user && (review.user_id === user._id || review.user_id === user.id) && (
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteReview(review._id)}
                        color="error"
                      >
                        <Delete />
                      </IconButton>
                    )}
                  </Box>

                  {review.content && (
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      {review.content}
                    </Typography>
                  )}

                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    {new Date(review.created_at).toLocaleDateString('pl-PL', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric'
                    })}
                  </Typography>
                </CardContent>
              </Card>
            ))}
          </Box>
        )}
      </Paper>

      {/* Dialog potwierdzenia wypożyczenia */}
      <Dialog open={borrowDialog} onClose={() => setBorrowDialog(false)}>
        <DialogTitle>Potwierdź wypożyczenie</DialogTitle>
        <DialogContent>
          <Typography>
            Czy na pewno chcesz wypożyczyć książkę "{book.title}"?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Termin zwrotu: 30 dni od daty wypożyczenia
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBorrowDialog(false)}>Anuluj</Button>
          <Button
            variant="contained"
            onClick={handleBorrow}
            disabled={borrowing}
          >
            {borrowing ? 'Wypożyczanie...' : 'Wypożycz'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default BookDetails;