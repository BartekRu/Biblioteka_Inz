/**
 * BookCard.jsx - Reusable book card component with Steam-inspired design
 */

import React, { useState } from 'react';
import {
  Card,
  CardMedia,
  CardContent,
  Box,
  Typography,
  IconButton,
  Chip,
  Rating,
  Tooltip,
} from '@mui/material';
import { Bookmark, BookmarkBorder, InfoOutlined } from '@mui/icons-material';
import { COLORS, animations } from '../../styles/theme';
import {
  getBookImage,
  getBookGenres,
  getBookRating,
  getBookReviewCount,
  isBookAvailable,
  getMatchScorePercent,
  truncateText,
  getRecommendationReason,
} from '../../utils/bookHelpers';
import { recommendationsAPI } from '../../../../services/api';

const BookCard = ({
  book,
  onClick,
  showScore = true,
  showReason = false,
  compact = false,
  interactionSource = 'unknown',
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const [bookmarked, setBookmarked] = useState(book.onWishlist || false);

  const handleBookmark = async (e) => {
    e.stopPropagation();
    const newValue = !bookmarked;
    setBookmarked(newValue);

    try {
      await recommendationsAPI.reportInteraction(
        book._id,
        newValue ? 'wishlist_add' : 'wishlist_remove',
        { source: interactionSource }
      );
    } catch (err) {
      console.error('Failed to report wishlist interaction', err);
      setBookmarked(!newValue); // Rollback on error
    }
  };

  const genres = getBookGenres(book);
  const available = isBookAvailable(book);
  const rating = getBookRating(book);
  const reviewCount = getBookReviewCount(book);
  const matchScore = getMatchScorePercent(book);
  const reason = getRecommendationReason(book);

  return (
    <Card
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      sx={{
        width: compact ? 150 : 180,
        flexShrink: 0,
        bgcolor: 'transparent',
        cursor: 'pointer',
        ...animations.cardHover,
      }}
      elevation={0}
    >
      {/* Cover Image */}
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
          height={compact ? 200 : 240}
          image={getBookImage(book)}
          alt={book.title}
          sx={{ objectFit: 'cover' }}
        />

        {/* Hover Overlay */}
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
            {truncateText(book.description, 100)}
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

        {/* Bookmark Button */}
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

        {/* Availability Badge */}
        <Box
          sx={{
            position: 'absolute',
            bottom: 8,
            left: 8,
            bgcolor: available ? 'rgba(76, 175, 80, 0.9)' : 'rgba(244, 67, 54, 0.9)',
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

        {/* Match Score Badge */}
        {showScore && matchScore && (
          <Tooltip title="Dopasowanie do Twoich preferencji">
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
              {matchScore}%
            </Box>
          </Tooltip>
        )}
      </Box>

      {/* Card Content */}
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
        <Typography variant="caption" sx={{ color: COLORS.textSecondary, display: 'block' }}>
          {book.author}
        </Typography>

        {/* Rating */}
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

        {/* Recommendation Reason */}
        {showReason && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
            <InfoOutlined sx={{ fontSize: 12, color: COLORS.textSecondary }} />
            <Typography
              variant="caption"
              sx={{
                color: COLORS.accent,
                fontSize: '0.65rem',
                fontStyle: 'italic',
              }}
            >
              {reason}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default BookCard;
