/**
 * RecommendationsPage.jsx
 *
 * Strona rekomendacji książek inspirowana interfejsem Steam
 * Pokazuje wyniki modelu LightGCN w różnych sekcjach
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardMedia,
  CardContent,
  IconButton,
  Chip,
  Button,
  Rating,
  Skeleton,
  Tooltip,
  Paper,
  Divider,
  Alert,
  Collapse,
} from '@mui/material';
import {
  ChevronLeft,
  ChevronRight,
  AutoAwesome,
  TrendingUp,
  LocalLibrary,
  Psychology,
  Category,
  Bookmark,
  BookmarkBorder,
  Star,
  Search,
  Refresh,
  Info,
  BarChart,
  Speed,
  Diversity3,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { recommendationsAPI } from '../../services/api';

// ============================================================================
// STYLE CONSTANTS - Steam-inspired dark theme for library
// ============================================================================

const COLORS = {
  bgDark: '#1b2838',
  bgMedium: '#2a475e',
  bgLight: '#66c0f4',
  accent: '#66c0f4',
  accentDark: '#1a9fff',
  textPrimary: '#c7d5e0',
  textSecondary: '#8f98a0',
  cardBg: 'linear-gradient(135deg, #1e3a50 0%, #2a475e 100%)',
  cardHover: 'linear-gradient(135deg, #2a4a65 0%, #3a5a75 100%)',
  goldAccent: '#ffc107',
  successGreen: '#4caf50',
};

const pageStyles = {
  mainContainer: {
    minHeight: '100vh',
    background: `linear-gradient(180deg, ${COLORS.bgDark} 0%, #0f1923 100%)`,
    py: 4,
  },
  sectionTitle: {
    color: COLORS.textPrimary,
    fontWeight: 300,
    textTransform: 'uppercase',
    letterSpacing: '2px',
    fontSize: '0.9rem',
    mb: 2,
    display: 'flex',
    alignItems: 'center',
    gap: 1,
  },
  carouselContainer: {
    position: 'relative',
    mb: 6,
  },
  navButton: {
    position: 'absolute',
    top: '50%',
    transform: 'translateY(-50%)',
    bgcolor: 'rgba(0,0,0,0.7)',
    color: 'white',
    '&:hover': {
      bgcolor: 'rgba(0,0,0,0.9)',
    },
    zIndex: 10,
  },
};

// ============================================================================
// HELPERY DO MAPOWANIA PÓL Z BACKENDU
// ============================================================================

const getBookImage = (book) =>
  book?.coverImage ||
  book?.image_url ||
  book?.small_image_url ||
  '/default-book-cover.jpg';

const getBookGenres = (book) => book?.genres || book?.genre || [];

const getBookRating = (book) =>
  book?.averageRating ??
  book?.average_rating ??
  0;

const getBookReviewCount = (book) =>
  book?.reviewCount ??
  book?.total_reviews ??
  book?.ratings_count ??
  book?.reviews_count ??
  0;

const isBookAvailable = (book) => {
  if (typeof book?.available === 'boolean') return book.available;
  if (typeof book?.available_copies === 'number') {
    return book.available_copies > 0;
  }
  return true;
};

// ============================================================================
// FEATURED CAROUSEL - Główny carousel z wyróżnionymi rekomendacjami
// ============================================================================

const FeaturedCarousel = ({ books, loading }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const navigate = useNavigate();

  const nextSlide = useCallback(() => {
    if (!books.length) return;
    setCurrentIndex((prev) => (prev + 1) % books.length);
  }, [books.length]);

  const prevSlide = () => {
    if (!books.length) return;
    setCurrentIndex((prev) => (prev - 1 + books.length) % books.length);
  };

  useEffect(() => {
    const timer = setInterval(nextSlide, 6000);
    return () => clearInterval(timer);
  }, [nextSlide]);

  if (loading) {
    return (
      <Box sx={{ height: 400, position: 'relative', mb: 6 }}>
        <Skeleton
          variant="rectangular"
          width="100%"
          height={400}
          sx={{ bgcolor: COLORS.bgMedium, borderRadius: 2 }}
        />
      </Box>
    );
  }

  if (!books.length) return null;

  const currentBook = books[currentIndex];
  const genres = getBookGenres(currentBook);
  const available = isBookAvailable(currentBook);
  const rating = getBookRating(currentBook);

  return (
    <Box sx={pageStyles.carouselContainer}>
      <Typography sx={pageStyles.sectionTitle}>
        <AutoAwesome sx={{ color: COLORS.goldAccent }} />
        Wyróżnione i polecane dla Ciebie
      </Typography>

      <Box
        sx={{
          display: 'flex',
          borderRadius: 2,
          overflow: 'hidden',
          bgcolor: COLORS.bgMedium,
          height: 400,
          position: 'relative',
          boxShadow: '0 10px 40px rgba(0,0,0,0.5)',
        }}
      >
        {/* Main Image */}
        <Box
          sx={{
            flex: '0 0 65%',
            position: 'relative',
            overflow: 'hidden',
            cursor: 'pointer',
          }}
         onClick={() => {
    recommendationsAPI.reportInteraction(currentBook._id, 'click', {
      source: 'featured',
    });
    navigate(`/books/${currentBook._id}`);
  }}
>
          <Box
            component="img"
            src={getBookImage(currentBook)}
            alt={currentBook.title}
            sx={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transition: 'transform 0.5s ease',
              '&:hover': {
                transform: 'scale(1.02)',
              },
            }}
          />
          {/* Overlay gradient */}
          <Box
            sx={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: '50%',
              background:
                'linear-gradient(to top, rgba(27,40,56,0.95), transparent)',
            }}
          />
          {/* Title overlay */}
          <Box
            sx={{
              position: 'absolute',
              bottom: 20,
              left: 20,
              right: 20,
            }}
          >
            <Typography
              variant="h3"
              sx={{
                color: 'white',
                fontWeight: 700,
                textShadow: '2px 2px 8px rgba(0,0,0,0.8)',
                fontFamily: '"Playfair Display", serif',
              }}
            >
              {currentBook.title}
            </Typography>
            <Typography
              variant="h6"
              sx={{ color: COLORS.textSecondary, mt: 1 }}
            >
              {currentBook.author}
            </Typography>
          </Box>
          {/* Bookmark badge */}
          {currentBook.onWishlist && (
            <Box
              sx={{
                position: 'absolute',
                top: 16,
                left: 16,
                bgcolor: COLORS.goldAccent,
                color: COLORS.bgDark,
                px: 1.5,
                py: 0.5,
                borderRadius: 1,
                display: 'flex',
                alignItems: 'center',
                gap: 0.5,
                fontSize: '0.75rem',
                fontWeight: 600,
              }}
            >
              <Star sx={{ fontSize: 14 }} />
              Na liście życzeń
            </Box>
          )}
        </Box>

        {/* Right panel - details */}
        <Box
          sx={{
            flex: '0 0 35%',
            p: 3,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          {/* Thumbnails grid */}
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: 1,
              mb: 2,
            }}
          >
            {[0, 1, 2, 3].map((idx) => (
              <Box
                key={idx}
                sx={{
                  aspectRatio: '16/9',
                  borderRadius: 1,
                  overflow: 'hidden',
                  opacity: 0.7,
                  '&:hover': { opacity: 1 },
                  transition: 'opacity 0.2s',
                }}
              >
                <Box
                  component="img"
                  src={currentBook.images?.[idx] || getBookImage(currentBook)}
                  alt=""
                  sx={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                  }}
                />
              </Box>
            ))}
          </Box>

          {/* Recommendation reason */}
          <Box sx={{ mb: 2 }}>
            <Chip
              icon={<Psychology />}
              label={currentBook.recommendationReason || 'Polecane przez AI'}
              sx={{
                bgcolor: 'rgba(102, 192, 244, 0.2)',
                color: COLORS.accent,
                border: `1px solid ${COLORS.accent}`,
                mb: 1,
              }}
            />
            <Typography variant="body2" sx={{ color: COLORS.textSecondary }}>
              {currentBook.description?.slice(0, 150)}...
            </Typography>
          </Box>

          {/* Tags */}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
            {genres.slice(0, 4).map((genre) => (
              <Chip
                key={genre}
                label={genre}
                size="small"
                sx={{
                  bgcolor: COLORS.bgDark,
                  color: COLORS.textSecondary,
                  fontSize: '0.7rem',
                }}
              />
            ))}
          </Box>

          {/* Availability */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <Box>
              <Typography
                variant="body2"
                sx={{
                  color: available ? COLORS.successGreen : '#ff6b6b',
                  fontWeight: 600,
                }}
              >
                {available ? 'Dostępna' : 'Wypożyczona'}
              </Typography>
              {currentBook.matchScore && (
                <Typography variant="caption" sx={{ color: COLORS.accent }}>
                  {Math.round(currentBook.matchScore * 100)}% dopasowania
                </Typography>
              )}
            </Box>
            <Rating
              value={rating}
              readOnly
              precision={0.5}
              size="small"
              sx={{
                '& .MuiRating-iconFilled': { color: COLORS.goldAccent },
              }}
            />
          </Box>
        </Box>

        {/* Navigation buttons */}
        <IconButton
          onClick={prevSlide}
          sx={{ ...pageStyles.navButton, left: 10 }}
        >
          <ChevronLeft />
        </IconButton>
        <IconButton
          onClick={nextSlide}
          sx={{ ...pageStyles.navButton, right: 10 }}
        >
          <ChevronRight />
        </IconButton>

        {/* Dots indicator */}
        <Box
          sx={{
            position: 'absolute',
            bottom: 10,
            left: '50%',
            transform: 'translateX(-50%)',
            display: 'flex',
            gap: 1,
          }}
        >
          {books.map((_, idx) => (
            <Box
              key={idx}
              onClick={() => setCurrentIndex(idx)}
              sx={{
                width: idx === currentIndex ? 24 : 8,
                height: 8,
                borderRadius: 4,
                bgcolor:
                  idx === currentIndex
                    ? COLORS.accent
                    : 'rgba(255,255,255,0.3)',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
              }}
            />
          ))}
        </Box>
      </Box>
    </Box>
  );
};

// ============================================================================
// CATEGORY CAROUSEL - Przeglądaj według kategorii
// ============================================================================

const CategoryCarousel = ({ categories, onCategoryClick, loading }) => {
  const scrollRef = React.useRef(null);

  const scroll = (direction) => {
    if (scrollRef.current) {
      const scrollAmount = 300;
      scrollRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      });
    }
  };

  if (loading) {
    return (
      <Box sx={{ mb: 6 }}>
        <Typography sx={pageStyles.sectionTitle}>
          <Category sx={{ color: COLORS.accent }} />
          Przeglądaj według kategorii
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, overflow: 'hidden' }}>
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton
              key={i}
              variant="rectangular"
              width={200}
              height={120}
              sx={{ borderRadius: 2, bgcolor: COLORS.bgMedium, flexShrink: 0 }}
            />
          ))}
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ mb: 6, position: 'relative' }}>
      <Typography sx={pageStyles.sectionTitle}>
        <Category sx={{ color: COLORS.accent }} />
        Przeglądaj według kategorii
      </Typography>

      <Box
        ref={scrollRef}
        sx={{
          display: 'flex',
          gap: 2,
          overflowX: 'auto',
          pb: 2,
          scrollbarWidth: 'none',
          '&::-webkit-scrollbar': { display: 'none' },
        }}
      >
        {categories.map((category) => (
          <Box
            key={category.name}
            onClick={() => onCategoryClick(category.name)}
            sx={{
              flexShrink: 0,
              width: 200,
              height: 120,
              borderRadius: 2,
              overflow: 'hidden',
              position: 'relative',
              cursor: 'pointer',
              transition: 'transform 0.3s ease, box-shadow 0.3s ease',
              '&:hover': {
                transform: 'scale(1.05)',
                boxShadow: '0 8px 25px rgba(102, 192, 244, 0.3)',
              },
            }}
          >
            {/* Background collage */}
            <Box
              sx={{
                position: 'absolute',
                inset: 0,
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '2px',
                filter: 'brightness(0.6)',
              }}
            >
              {category.sampleCovers?.slice(0, 6).map((cover, idx) => (
                <Box
                  key={idx}
                  component="img"
                  src={cover || '/default-book-cover.jpg'}
                  alt=""
                  sx={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              ))}
            </Box>
            {/* Category name overlay */}
            <Box
              sx={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background:
                  'linear-gradient(135deg, rgba(42,71,94,0.8), rgba(27,40,56,0.9))',
              }}
            >
              <Typography
                variant="subtitle1"
                sx={{
                  color: 'white',
                  fontWeight: 600,
                  textAlign: 'center',
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                  px: 2,
                }}
              >
                {category.name}
              </Typography>
            </Box>
            {/* Count badge */}
            <Box
              sx={{
                position: 'absolute',
                bottom: 8,
                right: 8,
                bgcolor: 'rgba(0,0,0,0.6)',
                color: COLORS.textSecondary,
                px: 1,
                py: 0.25,
                borderRadius: 1,
                fontSize: '0.7rem',
              }}
            >
              {category.count} książek
            </Box>
          </Box>
        ))}
      </Box>

      {/* Navigation arrows */}
      <IconButton
        onClick={() => scroll('left')}
        sx={{
          ...pageStyles.navButton,
          left: -20,
          top: '60%',
        }}
        size="small"
      >
        <ChevronLeft />
      </IconButton>
      <IconButton
        onClick={() => scroll('right')}
        sx={{
          ...pageStyles.navButton,
          right: -20,
          top: '60%',
        }}
        size="small"
      >
        <ChevronRight />
      </IconButton>
    </Box>
  );
};

// ============================================================================
// BECAUSE YOU BORROWED - "Ponieważ wypożyczyłeś X"
// ============================================================================

const BecauseYouSection = ({ sourceBook, recommendations, loading }) => {
  const navigate = useNavigate();
  const scrollRef = React.useRef(null);

  const scroll = (direction) => {
    if (scrollRef.current) {
      const scrollAmount = 250;
      scrollRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      });
    }
  };

  if (loading) {
    return (
      <Box sx={{ mb: 5 }}>
        <Skeleton
          width={300}
          height={24}
          sx={{ bgcolor: COLORS.bgMedium, mb: 2 }}
        />
        <Box sx={{ display: 'flex', gap: 2 }}>
          {[1, 2, 3, 4].map((i) => (
            <Skeleton
              key={i}
              variant="rectangular"
              width={180}
              height={280}
              sx={{ borderRadius: 1, bgcolor: COLORS.bgMedium }}
            />
          ))}
        </Box>
      </Box>
    );
  }

  if (!sourceBook || !recommendations?.length) return null;

  return (
    <Box sx={{ mb: 5, position: 'relative' }}>
      <Typography sx={pageStyles.sectionTitle}>
        Ponieważ wypożyczyłeś{' '}
        <Box
          component="span"
          sx={{ color: 'white', fontWeight: 600, textTransform: 'none' }}
        >
          {sourceBook.title}
        </Box>
      </Typography>

      <Box
        ref={scrollRef}
        sx={{
          display: 'flex',
          gap: 2,
          overflowX: 'auto',
          pb: 2,
          scrollbarWidth: 'none',
          '&::-webkit-scrollbar': { display: 'none' },
        }}
      >
        {recommendations.map((book) => (
          <BookCard
  key={book._id}
  book={book}
  onClick={() => {
    recommendationsAPI.reportInteraction(book._id, 'click', {
      source: 'because-borrowed',
      sourceBookId: sourceBook?._id,
    });
    navigate(`/books/${book._id}`);
  }}
/>


        ))}
      </Box>

      <IconButton
        onClick={() => scroll('left')}
        sx={{ ...pageStyles.navButton, left: -20, top: '55%' }}
        size="small"
      >
        <ChevronLeft />
      </IconButton>
      <IconButton
        onClick={() => scroll('right')}
        sx={{ ...pageStyles.navButton, right: -20, top: '55%' }}
        size="small"
      >
        <ChevronRight />
      </IconButton>
    </Box>
  );
};

// ============================================================================
// BOOK CARD - Pojedyncza karta książki
// ============================================================================

const BookCard = ({ book, onClick, showScore = true }) => {
  const [isHovered, setIsHovered] = useState(false);
  const [bookmarked, setBookmarked] = useState(book.onWishlist || false);

  const handleBookmark = async (e) => {
  e.stopPropagation();
  const newValue = !bookmarked;
  setBookmarked(newValue);

  try {
    await recommendationsAPI.reportInteraction(
      book._id,
      newValue ? 'wishlist_add' : 'wishlist_remove'
    );
  } catch (err) {
    console.error('Failed to report wishlist interaction', err);
  }
};


  const genres = getBookGenres(book);
  const available = isBookAvailable(book);
  const rating = getBookRating(book);
  const reviewCount = getBookReviewCount(book);

  return (
    <Card
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      sx={{
        width: 180,
        flexShrink: 0,
        bgcolor: 'transparent',
        cursor: 'pointer',
        transition: 'transform 0.3s ease',
        transform: isHovered ? 'scale(1.05)' : 'scale(1)',
        '&:hover': {
          '& .book-cover': {
            boxShadow: '0 8px 25px rgba(102, 192, 244, 0.4)',
          },
        },
      }}
      elevation={0}
    >
      <Box
        className="book-cover"
        sx={{
          position: 'relative',
          borderRadius: 1,
          overflow: 'hidden',
          transition: 'box-shadow 0.3s ease',
        }}
      >
        <CardMedia
          component="img"
          height="240"
          image={getBookImage(book)}
          alt={book.title}
          sx={{ objectFit: 'cover' }}
        />

        {/* Hover overlay */}
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            bgcolor: 'rgba(0,0,0,0.7)',
            opacity: isHovered ? 1 : 0,
            transition: 'opacity 0.3s ease',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'flex-end',
            p: 1.5,
          }}
        >
          <Typography
            variant="body2"
            sx={{
              color: 'white',
              fontSize: '0.75rem',
              lineHeight: 1.4,
              mb: 1,
            }}
          >
            {book.description?.slice(0, 100)}...
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {genres.slice(0, 3).map((genre) => (
              <Chip
                key={genre}
                label={genre}
                size="small"
                sx={{
                  height: 20,
                  fontSize: '0.65rem',
                  bgcolor: 'rgba(102, 192, 244, 0.3)',
                  color: COLORS.accent,
                }}
              />
            ))}
          </Box>
        </Box>

        {/* Bookmark button */}
        <IconButton
          onClick={handleBookmark}
          sx={{
            position: 'absolute',
            top: 4,
            right: 4,
            bgcolor: 'rgba(0,0,0,0.5)',
            color: bookmarked ? COLORS.goldAccent : 'white',
            opacity: isHovered || bookmarked ? 1 : 0,
            transition: 'opacity 0.2s',
            '&:hover': {
              bgcolor: 'rgba(0,0,0,0.7)',
            },
          }}
          size="small"
        >
          {bookmarked ? <Bookmark /> : <BookmarkBorder />}
        </IconButton>

        {/* Availability badge */}
        <Box
          sx={{
            position: 'absolute',
            bottom: 8,
            left: 8,
            bgcolor: available
              ? 'rgba(76, 175, 80, 0.9)'
              : 'rgba(244, 67, 54, 0.9)',
            color: 'white',
            px: 1,
            py: 0.25,
            borderRadius: 0.5,
            fontSize: '0.65rem',
            fontWeight: 600,
          }}
        >
          {available ? 'Dostępna' : 'Wypożyczona'}
        </Box>

        {/* Match score */}
        {showScore && book.matchScore && (
          <Box
            sx={{
              position: 'absolute',
              top: 8,
              left: 8,
              bgcolor: COLORS.accent,
              color: COLORS.bgDark,
              px: 1,
              py: 0.25,
              borderRadius: 0.5,
              fontSize: '0.7rem',
              fontWeight: 700,
            }}
          >
            {Math.round(book.matchScore * 100)}%
          </Box>
        )}
      </Box>

      <CardContent sx={{ px: 0, py: 1 }}>
        <Typography
          variant="body2"
          sx={{
            color: isHovered ? 'white' : COLORS.textPrimary,
            fontWeight: 500,
            lineHeight: 1.3,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            transition: 'color 0.3s',
          }}
        >
          {book.title}
        </Typography>
        <Typography
          variant="caption"
          sx={{ color: COLORS.textSecondary, display: 'block' }}
        >
          {book.author}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
          <Rating
            value={rating}
            readOnly
            size="small"
            precision={0.5}
            sx={{
              fontSize: '0.9rem',
              '& .MuiRating-iconFilled': { color: COLORS.goldAccent },
            }}
          />
          <Typography variant="caption" sx={{ color: COLORS.textSecondary }}>
            ({reviewCount})
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

// ============================================================================
// DISCOVERY QUEUE - Kolejka odkryć
// ============================================================================

const DiscoveryQueue = ({ books, onExplore, loading }) => {
  if (loading) {
    return (
      <Box sx={{ mb: 6 }}>
        <Skeleton
          width={200}
          height={24}
          sx={{ bgcolor: COLORS.bgMedium, mb: 2 }}
        />
        <Skeleton
          variant="rectangular"
          height={120}
          sx={{ bgcolor: COLORS.bgMedium, borderRadius: 2 }}
        />
      </Box>
    );
  }

  return (
    <Box sx={{ mb: 6 }}>
      <Typography sx={pageStyles.sectionTitle}>
        <Search sx={{ color: COLORS.accent }} />
        Twoja kolejka odkryć
      </Typography>

      <Paper
        onClick={onExplore}
        sx={{
          background: `linear-gradient(90deg, ${COLORS.bgMedium} 0%, ${COLORS.bgDark} 100%)`,
          borderRadius: 2,
          p: 2,
          display: 'flex',
          alignItems: 'center',
          cursor: 'pointer',
          transition: 'all 0.3s ease',
          border: `1px solid ${COLORS.bgMedium}`,
          '&:hover': {
            borderColor: COLORS.accent,
            boxShadow: '0 4px 20px rgba(102, 192, 244, 0.2)',
          },
        }}
      >
        {/* Preview covers */}
        <Box sx={{ display: 'flex', mr: 3 }}>
          {books?.slice(0, 6).map((book, idx) => (
            <Box
              key={book._id}
              component="img"
              src={getBookImage(book)}
              alt=""
              sx={{
                width: 60,
                height: 85,
                objectFit: 'cover',
                borderRadius: 1,
                border: '2px solid ' + COLORS.bgDark,
                ml: idx > 0 ? -2 : 0,
                zIndex: 6 - idx,
              }}
            />
          ))}
        </Box>

        {/* Text */}
        <Box sx={{ flex: 1 }}>
          <Typography
            variant="body1"
            sx={{ color: COLORS.textPrimary, mb: 0.5 }}
          >
            Kliknij tutaj, aby rozpocząć przeglądanie swojej kolejki odkryć
          </Typography>
          <Typography variant="body2" sx={{ color: COLORS.textSecondary }}>
            {books?.length || 0} książek czeka na odkrycie
          </Typography>
        </Box>

        {/* Arrow */}
        <Box
          sx={{
            width: 50,
            height: 50,
            borderRadius: '50%',
            bgcolor: COLORS.bgDark,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <ChevronRight sx={{ color: COLORS.accent, fontSize: 30 }} />
        </Box>
      </Paper>
    </Box>
  );
};

// ============================================================================
// MODEL METRICS PANEL - Panel pokazujący metryki modelu
// ============================================================================

const ModelMetricsPanel = ({ metrics, loading }) => {
  const [expanded, setExpanded] = useState(false);

  if (loading) {
    return (
      <Box sx={{ mb: 6 }}>
        <Skeleton
          width={300}
          height={24}
          sx={{ bgcolor: COLORS.bgMedium, mb: 2 }}
        />
        <Skeleton
          variant="rectangular"
          height={150}
          sx={{ bgcolor: COLORS.bgMedium, borderRadius: 2 }}
        />
      </Box>
    );
  }

  return (
    <Box sx={{ mb: 6 }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 2,
        }}
      >
        <Typography sx={pageStyles.sectionTitle}>
          <BarChart sx={{ color: COLORS.accent }} />
          Wydajność modelu rekomendacji
        </Typography>
        <Button
          size="small"
          startIcon={<Info />}
          onClick={() => setExpanded(!expanded)}
          sx={{ color: COLORS.textSecondary }}
        >
          {expanded ? 'Zwiń' : 'Szczegóły'}
        </Button>
      </Box>

      <Paper
        sx={{
          background: COLORS.cardBg,
          borderRadius: 2,
          p: 3,
          border: `1px solid ${COLORS.bgMedium}`,
        }}
      >
        {/* Main metrics */}
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
            gap: 3,
            mb: expanded ? 3 : 0,
          }}
        >
          <MetricBox
            icon={<TrendingUp />}
            label="Recall@20"
            value={metrics?.recall20 || 0.1411}
            format="percent"
            description="Trafność rekomendacji"
            color={COLORS.successGreen}
          />
          <MetricBox
            icon={<Speed />}
            label="NDCG@20"
            value={metrics?.ndcg20 || 0.0842}
            format="percent"
            description="Jakość rankingu"
            color={COLORS.accent}
          />
          <MetricBox
            icon={<Diversity3 />}
            label="Coverage"
            value={metrics?.coverage || 0.78}
            format="percent"
            description="Pokrycie katalogu"
            color={COLORS.goldAccent}
          />
          <MetricBox
            icon={<Psychology />}
            label="Model"
            value={metrics?.modelName || 'LightGCN'}
            format="text"
            description={`${metrics?.layers || 3} warstwy GCN`}
            color={COLORS.accent}
          />
        </Box>

        {/* Expanded details */}
        <Collapse in={expanded}>
          <Divider sx={{ borderColor: COLORS.bgMedium, mb: 2 }} />
          <Box>
            <Typography
              variant="subtitle2"
              sx={{ color: COLORS.textPrimary, mb: 1 }}
            >
              Szczegóły treningu modelu
            </Typography>
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: 2,
              }}
            >
              <DetailRow label="Dataset" value="goodbooks-10k" />
              <DetailRow
                label="Użytkownicy treningowi"
                value={metrics?.trainUsers || '35,710'}
              />
              <DetailRow
                label="Książki w modelu"
                value={metrics?.trainItems || '10,000'}
              />
              <DetailRow
                label="Interakcje"
                value={metrics?.interactions || '932,940'}
              />
              <DetailRow
                label="Embedding dim"
                value={metrics?.embeddingDim || '64'}
              />
              <DetailRow label="Epoki" value={metrics?.epochs || '50'} />
              <DetailRow
                label="Learning rate"
                value={metrics?.learningRate || '0.001'}
              />
              <DetailRow
                label="Ostatnia aktualizacja"
                value={metrics?.lastUpdated || 'Dzisiaj'}
              />
            </Box>
          </Box>
        </Collapse>
      </Paper>
    </Box>
  );
};

const MetricBox = ({ icon, label, value, format, description, color }) => (
  <Box sx={{ textAlign: 'center' }}>
    <Box
      sx={{
        color: color,
        mb: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 1,
      }}
    >
      {icon}
      <Typography variant="caption" sx={{ color: COLORS.textSecondary }}>
        {label}
      </Typography>
    </Box>
    <Typography
      variant="h4"
      sx={{ color: 'white', fontWeight: 700, fontFamily: 'monospace' }}
    >
      {format === 'percent' ? `${(value * 100).toFixed(2)}%` : value}
    </Typography>
    <Typography variant="caption" sx={{ color: COLORS.textSecondary }}>
      {description}
    </Typography>
  </Box>
);

const DetailRow = ({ label, value }) => (
  <Box
    sx={{
      display: 'flex',
      justifyContent: 'space-between',
      py: 0.5,
      borderBottom: `1px solid ${COLORS.bgDark}`,
    }}
  >
    <Typography variant="body2" sx={{ color: COLORS.textSecondary }}>
      {label}
    </Typography>
    <Typography variant="body2" sx={{ color: COLORS.textPrimary }}>
      {value}
    </Typography>
  </Box>
);

// ============================================================================
// FROM AUTHORS YOU KNOW - Od autorów których znasz
// ============================================================================

const FromAuthorsYouKnow = ({ authors, loading }) => {
  const navigate = useNavigate();
  const scrollRef = React.useRef(null);

  const scroll = (direction) => {
    if (scrollRef.current) {
      const scrollAmount = 280;
      scrollRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      });
    }
  };

  if (loading) {
    return (
      <Box sx={{ mb: 6 }}>
        <Skeleton
          width={350}
          height={24}
          sx={{ bgcolor: COLORS.bgMedium, mb: 2 }}
        />
        <Box sx={{ display: 'flex', gap: 2 }}>
          {[1, 2, 3, 4].map((i) => (
            <Skeleton
              key={i}
              variant="rectangular"
              width={260}
              height={200}
              sx={{ borderRadius: 2, bgcolor: COLORS.bgMedium }}
            />
          ))}
        </Box>
      </Box>
    );
  }

  if (!authors?.length) return null;

  return (
    <Box sx={{ mb: 6, position: 'relative' }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 2,
        }}
      >
        <Typography sx={pageStyles.sectionTitle}>
          <LocalLibrary sx={{ color: COLORS.accent }} />
          Od autorów których znasz
        </Typography>
        <Button
          size="small"
          sx={{ color: COLORS.accent }}
          onClick={() => navigate('/books?filter=known-authors')}
        >
          Przeglądaj wszystkie
        </Button>
      </Box>

      <Box
        ref={scrollRef}
        sx={{
          display: 'flex',
          gap: 2,
          overflowX: 'auto',
          pb: 2,
          scrollbarWidth: 'none',
          '&::-webkit-scrollbar': { display: 'none' },
        }}
      >
        {authors.map((author) => (
          <Paper
            key={author.name}
            sx={{
              flexShrink: 0,
              width: 260,
              background: COLORS.cardBg,
              borderRadius: 2,
              overflow: 'hidden',
              cursor: 'pointer',
              transition: 'all 0.3s ease',
              border: `1px solid transparent`,
              '&:hover': {
                borderColor: COLORS.accent,
                transform: 'translateY(-4px)',
              },
            }}
            onClick={() => navigate(`/books?author=${author.name}`)}
          >
            {/* Book cover preview */}
            <Box sx={{ position: 'relative', height: 140 }}>
              <Box
                component="img"
                src={
                  getBookImage(author.latestBook || {}) ||
                  '/default-book-cover.jpg'
                }
                alt=""
                sx={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  filter: 'brightness(0.7)',
                }}
              />
              {/* Availability badge */}
              {isBookAvailable(author.latestBook || {}) && (
                <Box
                  sx={{
                    position: 'absolute',
                    top: 8,
                    left: 8,
                    bgcolor: '#f44336',
                    color: 'white',
                    px: 1,
                    py: 0.25,
                    borderRadius: 0.5,
                    fontSize: '0.65rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.5,
                  }}
                >
                  ● Dostępne
                </Box>
              )}
            </Box>

            {/* Author info */}
            <Box sx={{ p: 2 }}>
              <Box
                sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}
              >
                <Box
                  sx={{
                    width: 32,
                    height: 32,
                    borderRadius: 0.5,
                    bgcolor: COLORS.bgDark,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.75rem',
                    color: COLORS.textSecondary,
                    fontWeight: 600,
                  }}
                >
                  {author.name.charAt(0)}
                </Box>
                <Typography
                  variant="body2"
                  sx={{ color: COLORS.textPrimary }}
                >
                  {author.name}
                </Typography>
              </Box>
              <Button
                size="small"
                variant="outlined"
                sx={{
                  color: COLORS.textSecondary,
                  borderColor: COLORS.bgDark,
                  fontSize: '0.7rem',
                  '&:hover': {
                    borderColor: COLORS.accent,
                    color: COLORS.accent,
                  },
                }}
              >
                Obserwuj
              </Button>
            </Box>
          </Paper>
        ))}
      </Box>

      <IconButton
        onClick={() => scroll('left')}
        sx={{ ...pageStyles.navButton, left: -20, top: '45%' }}
        size="small"
      >
        <ChevronLeft />
      </IconButton>
      <IconButton
        onClick={() => scroll('right')}
        sx={{ ...pageStyles.navButton, right: -20, top: '45%' }}
        size="small"
      >
        <ChevronRight />
      </IconButton>
    </Box>
  );
};

// ============================================================================
// BROWSE OPTIONS - Przyciski nawigacji (Nowości, Popularne, etc.)
// ============================================================================

const BrowseOptions = ({ onNavigate }) => {
  const options = [
    { label: 'Nowości', path: '/books?sort=newest', color: '#66c0f4' },
    { label: 'Popularne', path: '/books?sort=popular', color: '#66c0f4' },
    { label: 'Najwyżej oceniane', path: '/books?sort=rating', color: '#66c0f4' },
    { label: 'Według tagów', path: '/books/tags', color: '#66c0f4' },
  ];

  return (
    <Box sx={{ mb: 6 }}>
      <Typography sx={pageStyles.sectionTitle}>Przeglądaj katalog</Typography>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
          gap: 2,
        }}
      >
        {options.map((option) => (
          <Button
            key={option.label}
            onClick={() => onNavigate(option.path)}
            sx={{
              py: 2,
              background: `linear-gradient(135deg, ${COLORS.accent} 0%, ${COLORS.accentDark} 100%)`,
              color: 'white',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '1px',
              borderRadius: 1,
              '&:hover': {
                background: `linear-gradient(135deg, ${COLORS.accentDark} 0%, ${COLORS.accent} 100%)`,
                transform: 'scale(1.02)',
              },
              transition: 'all 0.3s ease',
            }}
          >
            {option.label}
          </Button>
        ))}
      </Box>
    </Box>
  );
};

// ============================================================================
// MAIN COMPONENT - Główny komponent strony
// ============================================================================

const RecommendationsPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // State for different sections
  const [featuredBooks, setFeaturedBooks] = useState([]);
  const [categories, setCategories] = useState([]);
  const [becauseSections, setBecauseSections] = useState([]);
  const [discoveryQueue, setDiscoveryQueue] = useState([]);
  const [knownAuthors, setKnownAuthors] = useState([]);
  const [modelMetrics, setModelMetrics] = useState(null);

  // Fetch all recommendations data
  useEffect(() => {
    const fetchRecommendations = async () => {
      if (!user) {
        navigate('/login');
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const [
  userRecRes,
  categoriesRes,
  becauseRes,
  queueRes,      // zostawiamy, na razie nie użyjemy
  authorsRes,
  metricsRes,
] = await Promise.allSettled([
  recommendationsAPI.getUserLightGCN(30),   // TU: LightGCN PRO
  recommendationsAPI.getCategories(),
  recommendationsAPI.getBecauseYouBorrowed(),
  recommendationsAPI.getDiscoveryQueue(),   // może się przydać jako fallback
  recommendationsAPI.getKnownAuthors(),
  recommendationsAPI.getModelMetrics(),
]);

if (userRecRes.status === 'fulfilled') {
  const recs = userRecRes.value.data || [];

  // główny carousel bierze pierwsze 10
  setFeaturedBooks(recs.slice(0, 10));

  // kolejka odkryć – cała lista (albo np. od 10. pozycji)
  setDiscoveryQueue(recs); 
}

if (categoriesRes.status === 'fulfilled') {
  setCategories(categoriesRes.value.data || []);
}
if (becauseRes.status === 'fulfilled') {
  setBecauseSections(becauseRes.value.data || []);
}
if (authorsRes.status === 'fulfilled') {
  setKnownAuthors(authorsRes.value.data || []);
}
if (metricsRes.status === 'fulfilled') {
  setModelMetrics(metricsRes.value.data);
}

      } catch (err) {
        console.error('Error fetching recommendations:', err);
        setError('Nie udało się załadować rekomendacji. Spróbuj ponownie.');
      } finally {
        setLoading(false);
      }
    };

    fetchRecommendations();
  }, [user, navigate]);

  const handleCategoryClick = (category) => {
    navigate(`/books?genre=${category}`);
  };

  const handleExploreQueue = () => {
    navigate('/discovery-queue');
  };

  const handleRefresh = () => {
    window.location.reload();
  };

  if (!user) {
    return null;
  }

  return (
    <Box sx={pageStyles.mainContainer}>
      <Container maxWidth="lg">
        {/* Header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mb: 4,
          }}
        >
          <Box>
            <Typography
              variant="h4"
              sx={{
                color: 'white',
                fontWeight: 300,
                fontFamily: '"Playfair Display", serif',
              }}
            >
              Twoje rekomendacje
            </Typography>
            <Typography variant="body2" sx={{ color: COLORS.textSecondary }}>
              Spersonalizowane dla Ciebie przez AI
            </Typography>
          </Box>
          <Tooltip title="Odśwież rekomendacje">
            <IconButton
              onClick={handleRefresh}
              sx={{ color: COLORS.textSecondary }}
            >
              <Refresh />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Error alert */}
        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Model Metrics Panel */}
        <ModelMetricsPanel metrics={modelMetrics} loading={loading} />

        {/* Featured Carousel */}
        <FeaturedCarousel books={featuredBooks} loading={loading} />

        {/* Discovery Queue */}
        <DiscoveryQueue
          books={discoveryQueue}
          onExplore={handleExploreQueue}
          loading={loading}
        />

        {/* Browse Options */}
        <BrowseOptions onNavigate={navigate} />

        {/* Categories */}
        <CategoryCarousel
          categories={categories}
          onCategoryClick={handleCategoryClick}
          loading={loading}
        />

        {/* Because You Borrowed sections */}
        {becauseSections.map((section, idx) => (
          <BecauseYouSection
            key={section.sourceBook?._id || idx}
            sourceBook={section.sourceBook}
            recommendations={section.recommendations}
            loading={loading}
          />
        ))}

        {/* From Authors You Know */}
        <FromAuthorsYouKnow authors={knownAuthors} loading={loading} />

        {/* Footer info */}
        <Box
          sx={{
            textAlign: 'center',
            py: 4,
            borderTop: `1px solid ${COLORS.bgMedium}`,
            mt: 4,
          }}
        >
          <Typography variant="body2" sx={{ color: COLORS.textSecondary }}>
            Rekomendacje generowane przez model LightGCN wytrenowany na{' '}
            {modelMetrics?.interactions || '932,940'} interakcjach
          </Typography>
          <Typography
            variant="caption"
            sx={{ color: COLORS.textSecondary, display: 'block', mt: 1 }}
          >
            Im więcej wypożyczasz i oceniasz książek, tym lepsze rekomendacje
            otrzymasz
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default RecommendationsPage;
