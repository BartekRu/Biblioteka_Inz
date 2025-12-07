import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Grid,
  Card,
  CardContent,
  CardMedia,
  Typography,
  TextField,
  Box,
  Chip,
  Button,
  CircularProgress,
  Alert,
  Pagination,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Rating,
  InputAdornment,
  Paper,
  Skeleton
} from '@mui/material';
import { Search, FilterList, Clear } from '@mui/icons-material';
import { booksAPI } from '../../services/api';
import { useNavigate, useSearchParams } from 'react-router-dom';

const BOOKS_PER_PAGE = 12;

// Popularne gatunki do filtrowania
const POPULAR_GENRES = [
  'Fantasy',
  'Fiction',
  'Romance',
  'Mystery',
  'Thriller',
  'Science Fiction',
  'Young Adult',
  'Classics',
  'Horror',
  'Biography',
  'History',
  'Non Fiction'
];

const Books = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Stan
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Paginacja
  const [page, setPage] = useState(parseInt(searchParams.get('page')) || 1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalBooks, setTotalBooks] = useState(0);

  // Filtry
  const [searchTerm, setSearchTerm] = useState(searchParams.get('search') || '');
  const [selectedGenre, setSelectedGenre] = useState(searchParams.get('genre') || '');
  const [sortBy, setSortBy] = useState(searchParams.get('sort') || 'title');

  // Debounce search
  const [debouncedSearch, setDebouncedSearch] = useState(searchTerm);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Fetch books
  const fetchBooks = useCallback(async () => {
    try {
      setLoading(true);
      const params = {
        page,
        limit: BOOKS_PER_PAGE,
        sort: sortBy,
      };
      
      if (debouncedSearch) params.search = debouncedSearch;
      if (selectedGenre) params.genre = selectedGenre;

      const response = await booksAPI.getAll(params);
      
      if (response.data.books) {
        setBooks(response.data.books);
        setTotalPages(response.data.total_pages || 1);
        setTotalBooks(response.data.total || 0);
      } else {
        setBooks(response.data);
        setTotalPages(1);
        setTotalBooks(response.data.length);
      }
      
      setError('');
    } catch (err) {
      console.error('Error fetching books:', err);
      setError('Błąd podczas pobierania książek');
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, selectedGenre, sortBy]);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (page > 1) params.set('page', page.toString());
    if (searchTerm) params.set('search', searchTerm);
    if (selectedGenre) params.set('genre', selectedGenre);
    if (sortBy !== 'title') params.set('sort', sortBy);
    setSearchParams(params);
  }, [page, searchTerm, selectedGenre, sortBy, setSearchParams]);

  const handlePageChange = (event, value) => {
    setPage(value);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleBookClick = (bookId) => {
    navigate(`/books/${bookId}`);
  };

  const handleClearFilters = () => {
    setSearchTerm('');
    setSelectedGenre('');
    setSortBy('title');
    setPage(1);
  };

  const hasActiveFilters = searchTerm || selectedGenre || sortBy !== 'title';

  const getBookImage = (book) => {
    if (book.image_url) return book.image_url;
    if (book.cover_image) return book.cover_image;
    return null;
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Katalog Książek
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {totalBooks > 0 ? `${totalBooks.toLocaleString()} książek w katalogu` : 'Ładowanie...'}
        </Typography>
      </Box>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              size="small"
              placeholder="Szukaj po tytule lub autorze..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
                endAdornment: searchTerm && (
                  <InputAdornment position="end">
                    <Clear 
                      sx={{ cursor: 'pointer' }} 
                      onClick={() => setSearchTerm('')}
                    />
                  </InputAdornment>
                )
              }}
            />
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Gatunek</InputLabel>
              <Select
                value={selectedGenre}
                label="Gatunek"
                onChange={(e) => {
                  setSelectedGenre(e.target.value);
                  setPage(1);
                }}
              >
                <MenuItem value="">Wszystkie gatunki</MenuItem>
                {POPULAR_GENRES.map((genre) => (
                  <MenuItem key={genre} value={genre}>{genre}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Sortuj</InputLabel>
              <Select
                value={sortBy}
                label="Sortuj"
                onChange={(e) => {
                  setSortBy(e.target.value);
                  setPage(1);
                }}
              >
                <MenuItem value="title">Tytuł (A-Z)</MenuItem>
                <MenuItem value="-title">Tytuł (Z-A)</MenuItem>
                <MenuItem value="-average_rating">Najwyżej oceniane</MenuItem>
                <MenuItem value="-ratings_count">Najpopularniejsze</MenuItem>
                <MenuItem value="-publication_year">Najnowsze</MenuItem>
                <MenuItem value="publication_year">Najstarsze</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={2}>
            {hasActiveFilters && (
              <Button
                fullWidth
                variant="outlined"
                startIcon={<Clear />}
                onClick={handleClearFilters}
              >
                Wyczyść
              </Button>
            )}
          </Grid>
        </Grid>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Grid container spacing={3}>
          {[...Array(BOOKS_PER_PAGE)].map((_, index) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={index}>
              <Card sx={{ height: '100%' }}>
                <Skeleton variant="rectangular" height={280} />
                <CardContent>
                  <Skeleton variant="text" height={32} />
                  <Skeleton variant="text" width="60%" />
                  <Skeleton variant="text" width="40%" />
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      ) : books.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            Nie znaleziono książek
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Spróbuj zmienić kryteria wyszukiwania
          </Typography>
          {hasActiveFilters && (
            <Button 
              variant="contained" 
              sx={{ mt: 2 }}
              onClick={handleClearFilters}
            >
              Wyczyść filtry
            </Button>
          )}
        </Box>
      ) : (
        <>
          <Grid container spacing={3}>
            {books.map((book) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={book._id}>
                <Card
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease-in-out',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: 8
                    }
                  }}
                  onClick={() => handleBookClick(book._id)}
                >
                  <CardMedia
                    component="div"
                    sx={{
                      height: 280,
                      bgcolor: 'grey.200',
                      backgroundImage: getBookImage(book)
                        ? `url(${getBookImage(book)})`
                        : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      position: 'relative'
                    }}
                  >
                    {!getBookImage(book) && (
                      <Typography
                        variant="h6"
                        sx={{
                          color: 'white',
                          textAlign: 'center',
                          px: 2,
                          textShadow: '1px 1px 2px rgba(0,0,0,0.5)'
                        }}
                      >
                        {book.title}
                      </Typography>
                    )}
                    
                    <Chip
                      label={book.available_copies > 0 ? 'Dostępna' : 'Wypożyczona'}
                      color={book.available_copies > 0 ? 'success' : 'error'}
                      size="small"
                      sx={{
                        position: 'absolute',
                        top: 8,
                        right: 8
                      }}
                    />
                  </CardMedia>

                  <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                    <Typography
                      variant="subtitle1"
                      component="h2"
                      sx={{
                        fontWeight: 600,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        minHeight: 48
                      }}
                    >
                      {book.title}
                    </Typography>

                    <Typography variant="body2" color="text.secondary" gutterBottom noWrap>
                      {book.author}
                    </Typography>

                    <Box sx={{ mt: 1, mb: 1, minHeight: 24 }}>
                      {(book.genre || []).slice(0, 2).map((genre, index) => (
                        <Chip
                          key={index}
                          label={genre}
                          size="small"
                          variant="outlined"
                          sx={{ mr: 0.5, mb: 0.5, fontSize: '0.7rem' }}
                        />
                      ))}
                    </Box>

                    <Box sx={{ mt: 'auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Rating
                          value={book.average_rating || 0}
                          precision={0.1}
                          size="small"
                          readOnly
                        />
                        <Typography variant="caption" sx={{ ml: 0.5 }}>
                          {(book.average_rating || 0).toFixed(1)}
                        </Typography>
                      </Box>
                      
                      {book.publication_year && (
                        <Typography variant="caption" color="text.secondary">
                          {book.publication_year}
                        </Typography>
                      )}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          {totalPages > 1 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
              <Pagination
                count={totalPages}
                page={page}
                onChange={handlePageChange}
                color="primary"
                size="large"
                showFirstButton
                showLastButton
              />
            </Box>
          )}
        </>
      )}
    </Container>
  );
};

export default Books;