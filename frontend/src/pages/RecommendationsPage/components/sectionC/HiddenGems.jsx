import React from 'react';
import { Box, Chip, Badge } from '@mui/material';
import { AutoAwesome, TrendingDown, Star } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import SectionTitle from '../shared/SectionTitle';
import HorizontalBookScroll from '../shared/HorizontalBookScroll';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import { COLORS, pageStyles } from '../../styles/theme';
import { recommendationsAPI } from '../../../../services/api';

const HiddenGems = ({ books, loading }) => {
  const navigate = useNavigate();

  const handleBookClick = async (book) => {
    await recommendationsAPI.reportInteraction(book._id, 'view', {
      source: 'hidden-gems',
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
  const avgBorrows = books.reduce((sum, b) => sum + (b.borrow_count || 0), 0) / books.length;

  return (
    <Box sx={pageStyles.sectionContainer}>
      <SectionTitle
        icon={AutoAwesome}
        title="Ukryte skarby"
        subtitle="Mało znane perełki, które warto odkryć"
      />

      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <Badge badgeContent={books.length} color="primary" max={99}>
          <Chip
            icon={<TrendingDown sx={{ fontSize: 14 }} />}
            label="Niedocenione"
            size="small"
            sx={{
              bgcolor: 'rgba(156, 39, 176, 0.2)',
              color: '#ce93d8',
              border: '1px solid #ce93d8',
            }}
          />
        </Badge>
        <Chip
          icon={<Star sx={{ fontSize: 14 }} />}
          label={`Śr. ocena: ${avgRating.toFixed(1)}/5.0`}
          size="small"
          sx={{
            bgcolor: 'rgba(255, 193, 7, 0.2)',
            color: COLORS.goldAccent,
            border: `1px solid ${COLORS.goldAccent}`,
          }}
        />
        <Chip
          label={`Śr. ${avgBorrows.toFixed(0)} wypożyczeń`}
          size="small"
          sx={{
            bgcolor: 'rgba(102, 192, 244, 0.2)',
            color: COLORS.accent,
            border: `1px solid ${COLORS.accent}`,
          }}
        />
      </Box>

      <HorizontalBookScroll
        books={books.slice(0, 30)}
        onBookClick={handleBookClick}
        showScore={true}
        showReason={false}
        interactionSource="hidden-gems"
      />
    </Box>
  );
};

export default HiddenGems;
