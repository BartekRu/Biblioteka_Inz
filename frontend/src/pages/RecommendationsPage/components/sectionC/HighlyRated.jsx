import React from 'react';
import { Box, Chip, Paper, Typography, LinearProgress } from '@mui/material';
import { Star, TrendingUp, Verified } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import SectionTitle from '../shared/SectionTitle';
import HorizontalBookScroll from '../shared/HorizontalBookScroll';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import { COLORS, pageStyles } from '../../styles/theme';
import { recommendationsAPI } from '../../../../services/api';

const HighlyRated = ({ books, minRating = 4.5, loading }) => {
  const navigate = useNavigate();

  const handleBookClick = async (book) => {
    await recommendationsAPI.reportInteraction(book._id, 'view', {
      source: 'highly-rated',
    });
    navigate(`/books/${book._id}`);
  };

  if (loading) {
    return (
      <Box sx={pageStyles.sectionContainer}>
        <LoadingSkeleton.Section cardCount={4} />
      </Box>
    );
  }

  if (!books || books.length === 0) {
    return null;
  }

  const avgRating =
    books.reduce((sum, b) => sum + (b.average_rating || b.averageRating || 0), 0) / books.length;

  const topRated = books.reduce((max, book) => {
    const rating = book.average_rating || book.averageRating || 0;
    const maxRating = max.average_rating || max.averageRating || 0;
    return rating > maxRating ? book : max;
  }, books[0]);

  const topRatedScore = topRated.average_rating || topRated.averageRating || 0;

  return (
    <Box sx={pageStyles.sectionContainer}>
      <SectionTitle
        icon={Star}
        title="Wysoko oceniane odkrycia"
        subtitle={`Najlepsze książki według czytelników (≥${minRating}/5.0)`}
      />

      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <Chip
            icon={<Verified sx={{ fontSize: 14 }} />}
            label="Gwarancja jakości"
            size="small"
            sx={{
              bgcolor: 'rgba(76, 175, 80, 0.2)',
              color: COLORS.successGreen,
              border: `1px solid ${COLORS.successGreen}`,
            }}
          />
          <Chip
            icon={<Star sx={{ fontSize: 14 }} />}
            label={`Śr. ocena: ${avgRating.toFixed(2)}/5.0`}
            size="small"
            sx={{
              bgcolor: 'rgba(255, 193, 7, 0.2)',
              color: COLORS.goldAccent,
              border: `1px solid ${COLORS.goldAccent}`,
            }}
          />
          <Chip
            icon={<TrendingUp sx={{ fontSize: 14 }} />}
            label={`Top: ${topRatedScore.toFixed(2)}/5.0`}
            size="small"
            sx={{
              bgcolor: 'rgba(102, 192, 244, 0.2)',
              color: COLORS.accent,
              border: `1px solid ${COLORS.accent}`,
            }}
          />
        </Box>

        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="caption" sx={{ color: COLORS.textSecondary }}>
              Poziom jakości
            </Typography>
            <Typography variant="caption" sx={{ color: COLORS.successGreen, fontWeight: 600 }}>
              {Math.round((avgRating / 5.0) * 100)}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={(avgRating / 5.0) * 100}
            sx={{
              height: 6,
              borderRadius: 3,
              bgcolor: COLORS.bgDark,
              '& .MuiLinearProgress-bar': {
                bgcolor: COLORS.successGreen,
              },
            }}
          />
        </Box>
      </Box>

      <HorizontalBookScroll
        books={books.slice(0, 15)}
        onBookClick={handleBookClick}
        showScore={true}
        showReason={false}
        interactionSource="highly-rated"
      />

      <Paper
        sx={{
          mt: 2,
          p: 2,
          background: 'rgba(76, 175, 80, 0.05)',
          border: `1px solid ${COLORS.bgMedium}`,
          borderRadius: 1,
        }}
      >
        <Typography variant="caption" sx={{ color: COLORS.textSecondary, display: 'block', mb: 1 }}>
          ⭐ <strong>Jak to działa?</strong> Wybieramy książki z oceną ≥{minRating}/5.0 w Twoich
          ulubionych gatunkach, a następnie używamy LightGCN do personalizowanego rankingu.
          Balansujemy między wysoką oceną (30%) a dopasowaniem do Twojego profilu (70%).
        </Typography>
        <Typography variant="caption" sx={{ color: COLORS.textSecondary, fontStyle: 'italic' }}>
          ✅ Bezpieczny wybór - te książki spodoba się większości czytelników!
        </Typography>
      </Paper>
    </Box>
  );
};

export default HighlyRated;
