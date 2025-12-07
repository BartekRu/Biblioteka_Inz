
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
  LinearProgress,
  Tooltip,
  Fade,
  Zoom,
  Skeleton,
  Alert,
} from '@mui/material';
import {
  Close,
  Favorite,
  BookmarkAdd,
  ArrowBack,
  Undo,
  Info,
  LocalLibrary,
  AutoAwesome,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { recommendationsAPI } from '../../services/api';

// ============================================================================
// STYLE CONSTANTS
// ============================================================================

const COLORS = {
  bgDark: '#1b2838',
  bgMedium: '#2a475e',
  accent: '#66c0f4',
  textPrimary: '#c7d5e0',
  textSecondary: '#8f98a0',
  like: '#4caf50',
  dislike: '#f44336',
  wishlist: '#ffc107',
};

// ============================================================================
// BOOK CARD COMPONENT
// ============================================================================

const QueueBookCard = ({ book, onAction, isAnimating, animationDirection }) => {
  const [showDetails, setShowDetails] = useState(false);

  const getAnimationStyle = () => {
    if (!isAnimating) return {};
    
    const transforms = {
      left: 'translateX(-150%) rotate(-20deg)',
      right: 'translateX(150%) rotate(20deg)',
      up: 'translateY(-150%)',
    };
    
    return {
      transform: transforms[animationDirection],
      opacity: 0,
      transition: 'all 0.4s ease-out',
    };
  };

  return (
    <Card
      sx={{
        width: '100%',
        maxWidth: 500,
        height: 700,
        borderRadius: 4,
        overflow: 'hidden',
        position: 'relative',
        boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
        ...getAnimationStyle(),
      }}
    >
      {/* Cover Image */}
      <Box sx={{ position: 'relative', height: '60%' }}>
        <CardMedia
          component="img"
          image={book.coverImage || '/default-book-cover.jpg'}
          alt={book.title}
          sx={{
            height: '100%',
            objectFit: 'cover',
          }}
        />
        
        {/* Gradient overlay */}
        <Box
          sx={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: '50%',
            background: 'linear-gradient(to top, rgba(27,40,56,1), transparent)',
          }}
        />

        {/* Match score badge */}
        {book.matchScore && (
          <Box
            sx={{
              position: 'absolute',
              top: 16,
              right: 16,
              bgcolor: COLORS.accent,
              color: COLORS.bgDark,
              px: 2,
              py: 0.5,
              borderRadius: 2,
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
            }}
          >
            <AutoAwesome sx={{ fontSize: 16 }} />
            {Math.round(book.matchScore * 100)}% match
          </Box>
        )}

        {/* Availability badge */}
        <Box
          sx={{
            position: 'absolute',
            top: 16,
            left: 16,
            bgcolor: book.available ? COLORS.like : COLORS.dislike,
            color: 'white',
            px: 1.5,
            py: 0.5,
            borderRadius: 1,
            fontSize: '0.75rem',
            fontWeight: 600,
          }}
        >
          {book.available ? '✓ Dostępna' : '✗ Wypożyczona'}
        </Box>

        {/* Info button */}
        <IconButton
          onClick={() => setShowDetails(!showDetails)}
          sx={{
            position: 'absolute',
            bottom: 16,
            right: 16,
            bgcolor: 'rgba(0,0,0,0.5)',
            color: 'white',
            '&:hover': { bgcolor: 'rgba(0,0,0,0.7)' },
          }}
        >
          <Info />
        </IconButton>
      </Box>

      {/* Book Info */}
      <CardContent
        sx={{
          height: '40%',
          bgcolor: COLORS.bgDark,
          color: 'white',
          display: 'flex',
          flexDirection: 'column',
          p: 3,
        }}
      >
        <Typography
          variant="h5"
          sx={{
            fontWeight: 700,
            mb: 0.5,
            fontFamily: '"Playfair Display", serif',
            lineHeight: 1.2,
          }}
        >
          {book.title}
        </Typography>
        
        <Typography
          variant="subtitle1"
          sx={{ color: COLORS.textSecondary, mb: 2 }}
        >
          {book.author}
        </Typography>

        {/* Rating */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Rating
            value={book.averageRating || 0}
            readOnly
            precision={0.5}
            sx={{
              '& .MuiRating-iconFilled': { color: COLORS.wishlist },
            }}
          />
          <Typography variant="body2" sx={{ color: COLORS.textSecondary }}>
            ({book.reviewCount || 0} ocen)
          </Typography>
        </Box>

        {/* Genres */}
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
          {book.genres?.slice(0, 4).map((genre) => (
            <Chip
              key={genre}
              label={genre}
              size="small"
              sx={{
                bgcolor: 'rgba(102, 192, 244, 0.2)',
                color: COLORS.accent,
                border: `1px solid ${COLORS.accent}`,
              }}
            />
          ))}
        </Box>

        {/* Description (expandable) */}
        <Fade in={showDetails}>
          <Box
            sx={{
              position: 'absolute',
              bottom: 100,
              left: 0,
              right: 0,
              bgcolor: 'rgba(27,40,56,0.95)',
              p: 3,
              display: showDetails ? 'block' : 'none',
            }}
          >
            <Typography
              variant="body2"
              sx={{ color: COLORS.textPrimary, lineHeight: 1.6 }}
            >
              {book.description?.slice(0, 300)}...
            </Typography>
          </Box>
        </Fade>

        {/* Recommendation reason */}
        {book.recommendationReason && (
          <Typography
            variant="caption"
            sx={{
              mt: 'auto',
              color: COLORS.accent,
              fontStyle: 'italic',
            }}
          >
            💡 {book.recommendationReason}
          </Typography>
        )}
      </CardContent>

      {/* Action overlay hints */}
      <Box
        sx={{
          position: 'absolute',
          top: '50%',
          left: 20,
          transform: 'translateY(-50%) rotate(-15deg)',
          border: `4px solid ${COLORS.dislike}`,
          color: COLORS.dislike,
          px: 2,
          py: 1,
          borderRadius: 2,
          fontWeight: 700,
          fontSize: '1.5rem',
          opacity: 0,
          transition: 'opacity 0.2s',
          pointerEvents: 'none',
          '.swipe-left &': { opacity: 1 },
        }}
      >
        NIE
      </Box>
      <Box
        sx={{
          position: 'absolute',
          top: '50%',
          right: 20,
          transform: 'translateY(-50%) rotate(15deg)',
          border: `4px solid ${COLORS.like}`,
          color: COLORS.like,
          px: 2,
          py: 1,
          borderRadius: 2,
          fontWeight: 700,
          fontSize: '1.5rem',
          opacity: 0,
          transition: 'opacity 0.2s',
          pointerEvents: 'none',
          '.swipe-right &': { opacity: 1 },
        }}
      >
        TAK
      </Box>
    </Card>
  );
};

// ============================================================================
// ACTION BUTTONS
// ============================================================================

const ActionButtons = ({ onDislike, onWishlist, onLike, onUndo, canUndo }) => (
  <Box
    sx={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      gap: 3,
      mt: 4,
    }}
  >
    {/* Undo */}
    <Tooltip title="Cofnij">
      <span>
        <IconButton
          onClick={onUndo}
          disabled={!canUndo}
          sx={{
            width: 50,
            height: 50,
            bgcolor: COLORS.bgMedium,
            color: COLORS.textSecondary,
            '&:hover': { bgcolor: 'rgba(102, 192, 244, 0.3)' },
            '&:disabled': { opacity: 0.3 },
          }}
        >
          <Undo />
        </IconButton>
      </span>
    </Tooltip>

    {/* Dislike */}
    <Tooltip title="Nie interesuje mnie">
      <IconButton
        onClick={onDislike}
        sx={{
          width: 70,
          height: 70,
          bgcolor: 'rgba(244, 67, 54, 0.1)',
          border: `2px solid ${COLORS.dislike}`,
          color: COLORS.dislike,
          transition: 'all 0.2s',
          '&:hover': {
            bgcolor: COLORS.dislike,
            color: 'white',
            transform: 'scale(1.1)',
          },
        }}
      >
        <Close sx={{ fontSize: 32 }} />
      </IconButton>
    </Tooltip>

    {/* Wishlist */}
    <Tooltip title="Dodaj do listy życzeń">
      <IconButton
        onClick={onWishlist}
        sx={{
          width: 60,
          height: 60,
          bgcolor: 'rgba(255, 193, 7, 0.1)',
          border: `2px solid ${COLORS.wishlist}`,
          color: COLORS.wishlist,
          transition: 'all 0.2s',
          '&:hover': {
            bgcolor: COLORS.wishlist,
            color: COLORS.bgDark,
            transform: 'scale(1.1)',
          },
        }}
      >
        <BookmarkAdd sx={{ fontSize: 28 }} />
      </IconButton>
    </Tooltip>

    {/* Like / Reserve */}
    <Tooltip title="Zarezerwuj książkę">
      <IconButton
        onClick={onLike}
        sx={{
          width: 70,
          height: 70,
          bgcolor: 'rgba(76, 175, 80, 0.1)',
          border: `2px solid ${COLORS.like}`,
          color: COLORS.like,
          transition: 'all 0.2s',
          '&:hover': {
            bgcolor: COLORS.like,
            color: 'white',
            transform: 'scale(1.1)',
          },
        }}
      >
        <Favorite sx={{ fontSize: 32 }} />
      </IconButton>
    </Tooltip>
  </Box>
);

// ============================================================================
// PROGRESS INDICATOR
// ============================================================================

const QueueProgress = ({ current, total }) => (
  <Box sx={{ width: '100%', maxWidth: 500, mx: 'auto', mb: 3 }}>
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'space-between',
        mb: 1,
      }}
    >
      <Typography variant="caption" sx={{ color: COLORS.textSecondary }}>
        Książka {current} z {total}
      </Typography>
      <Typography variant="caption" sx={{ color: COLORS.accent }}>
        {Math.round((current / total) * 100)}% ukończono
      </Typography>
    </Box>
    <LinearProgress
      variant="determinate"
      value={(current / total) * 100}
      sx={{
        height: 6,
        borderRadius: 3,
        bgcolor: COLORS.bgMedium,
        '& .MuiLinearProgress-bar': {
          bgcolor: COLORS.accent,
          borderRadius: 3,
        },
      }}
    />
  </Box>
);

// ============================================================================
// EMPTY STATE
// ============================================================================

const EmptyQueue = ({ onRefresh }) => (
  <Box
    sx={{
      textAlign: 'center',
      py: 8,
      px: 4,
    }}
  >
    <LocalLibrary
      sx={{ fontSize: 80, color: COLORS.bgMedium, mb: 3 }}
    />
    <Typography
      variant="h5"
      sx={{ color: COLORS.textPrimary, mb: 2 }}
    >
      Przejrzałeś wszystkie książki!
    </Typography>
    <Typography
      variant="body1"
      sx={{ color: COLORS.textSecondary, mb: 4 }}
    >
      Wróć później po więcej rekomendacji lub odśwież kolejkę
    </Typography>
    <Button
      variant="contained"
      onClick={onRefresh}
      sx={{
        bgcolor: COLORS.accent,
        color: COLORS.bgDark,
        '&:hover': { bgcolor: '#4fa8d5' },
      }}
    >
      Odśwież kolejkę
    </Button>
  </Box>
);

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const DiscoveryQueuePage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [queue, setQueue] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isAnimating, setIsAnimating] = useState(false);
  const [animationDirection, setAnimationDirection] = useState(null);

  // Statistics
  const [stats, setStats] = useState({
    liked: 0,
    disliked: 0,
    wishlisted: 0,
  });

  // Fetch queue
  useEffect(() => {
    const fetchQueue = async () => {
      if (!user) {
        navigate('/login');
        return;
      }

      try {
        setLoading(true);
        const response = await recommendationsAPI.getDiscoveryQueue(20);
        setQueue(response.data || []);
      } catch (err) {
        console.error('Error fetching discovery queue:', err);
        setError('Nie udało się załadować kolejki odkryć');
      } finally {
        setLoading(false);
      }
    };

    fetchQueue();
  }, [user, navigate]);

  const currentBook = queue[currentIndex];

  const handleAction = useCallback((action, direction) => {
    if (isAnimating || !currentBook) return;

    setIsAnimating(true);
    setAnimationDirection(direction);

    // Report interaction
    recommendationsAPI.reportInteraction(currentBook._id, action);

    // Update stats
    setStats(prev => ({
      ...prev,
      [action === 'like' ? 'liked' : action === 'dislike' ? 'disliked' : 'wishlisted']: prev[action === 'like' ? 'liked' : action === 'dislike' ? 'disliked' : 'wishlisted'] + 1
    }));

    // Save to history
    setHistory(prev => [...prev, { book: currentBook, action }]);

    // Animate out and move to next
    setTimeout(() => {
      setCurrentIndex(prev => prev + 1);
      setIsAnimating(false);
      setAnimationDirection(null);
    }, 400);
  }, [currentBook, isAnimating]);

  const handleLike = () => handleAction('like', 'right');
  const handleDislike = () => handleAction('dislike', 'left');
  const handleWishlist = () => handleAction('wishlist', 'up');

  const handleUndo = useCallback(() => {
    if (history.length === 0) return;

    const lastAction = history[history.length - 1];
    setHistory(prev => prev.slice(0, -1));
    setCurrentIndex(prev => prev - 1);

    // Revert stats
    const statKey = lastAction.action === 'like' ? 'liked' : 
                    lastAction.action === 'dislike' ? 'disliked' : 'wishlisted';
    setStats(prev => ({
      ...prev,
      [statKey]: Math.max(0, prev[statKey] - 1)
    }));
  }, [history]);

  const handleRefresh = async () => {
    setLoading(true);
    setCurrentIndex(0);
    setHistory([]);
    setStats({ liked: 0, disliked: 0, wishlisted: 0 });
    
    try {
      const response = await recommendationsAPI.getDiscoveryQueue(20);
      setQueue(response.data || []);
    } catch (err) {
      setError('Nie udało się odświeżyć kolejki');
    } finally {
      setLoading(false);
    }
  };

  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (isAnimating) return;
      
      switch (e.key) {
        case 'ArrowLeft':
          handleDislike();
          break;
        case 'ArrowRight':
          handleLike();
          break;
        case 'ArrowUp':
          handleWishlist();
          break;
        case 'z':
          if (e.ctrlKey || e.metaKey) {
            handleUndo();
          }
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleLike, handleDislike, handleWishlist, handleUndo, isAnimating]);

  if (!user) return null;

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: `linear-gradient(180deg, ${COLORS.bgDark} 0%, #0f1923 100%)`,
        py: 4,
      }}
    >
      <Container maxWidth="sm">
        {/* Header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mb: 4,
          }}
        >
          <IconButton
            onClick={() => navigate('/recommendations')}
            sx={{ color: COLORS.textSecondary }}
          >
            <ArrowBack />
          </IconButton>
          
          <Typography
            variant="h5"
            sx={{
              color: 'white',
              fontWeight: 300,
              fontFamily: '"Playfair Display", serif',
            }}
          >
            Kolejka odkryć
          </Typography>
          
          <Box sx={{ width: 40 }} /> {/* Spacer */}
        </Box>

        {/* Error */}
        {error && (
          <Alert 
            severity="error" 
            sx={{ mb: 3 }}
            onClose={() => setError(null)}
          >
            {error}
          </Alert>
        )}

        {/* Loading */}
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <Skeleton
              variant="rectangular"
              width={400}
              height={600}
              sx={{ borderRadius: 4, bgcolor: COLORS.bgMedium }}
            />
          </Box>
        )}

        {/* Content */}
        {!loading && (
          <>
            {currentBook ? (
              <>
                {/* Progress */}
                <QueueProgress 
                  current={currentIndex + 1} 
                  total={queue.length} 
                />

                {/* Card */}
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'center',
                    perspective: '1000px',
                  }}
                >
                  <QueueBookCard
                    book={currentBook}
                    onAction={handleAction}
                    isAnimating={isAnimating}
                    animationDirection={animationDirection}
                  />
                </Box>

                {/* Actions */}
                <ActionButtons
                  onDislike={handleDislike}
                  onWishlist={handleWishlist}
                  onLike={handleLike}
                  onUndo={handleUndo}
                  canUndo={history.length > 0}
                />

                {/* Keyboard hint */}
                <Typography
                  variant="caption"
                  sx={{
                    display: 'block',
                    textAlign: 'center',
                    color: COLORS.textSecondary,
                    mt: 3,
                  }}
                >
                  Użyj strzałek ← → ↑ lub kliknij przyciski
                </Typography>
              </>
            ) : (
              <EmptyQueue onRefresh={handleRefresh} />
            )}

            {/* Stats summary */}
            {currentIndex > 0 && (
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'center',
                  gap: 4,
                  mt: 4,
                  pt: 3,
                  borderTop: `1px solid ${COLORS.bgMedium}`,
                }}
              >
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h6" sx={{ color: COLORS.like }}>
                    {stats.liked}
                  </Typography>
                  <Typography variant="caption" sx={{ color: COLORS.textSecondary }}>
                    Zarezerwowane
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h6" sx={{ color: COLORS.wishlist }}>
                    {stats.wishlisted}
                  </Typography>
                  <Typography variant="caption" sx={{ color: COLORS.textSecondary }}>
                    Na liście
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h6" sx={{ color: COLORS.dislike }}>
                    {stats.disliked}
                  </Typography>
                  <Typography variant="caption" sx={{ color: COLORS.textSecondary }}>
                    Pominięte
                  </Typography>
                </Box>
              </Box>
            )}
          </>
        )}
      </Container>
    </Box>
  );
};

export default DiscoveryQueuePage;