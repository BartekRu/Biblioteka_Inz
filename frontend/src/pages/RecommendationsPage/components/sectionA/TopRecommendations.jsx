import React from 'react';
import { Box, Chip } from '@mui/material';
import { AutoAwesome, Science } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import SectionTitle from '../shared/SectionTitle';
import HorizontalBookScroll from '../shared/HorizontalBookScroll';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import { COLORS, pageStyles } from '../../styles/theme';
import { recommendationsAPI } from '../../../../services/api';

const TopRecommendations = ({ books, loading, mmrEnabled }) => {
  const navigate = useNavigate();

  const handleBookClick = async (book) => {
    await recommendationsAPI.reportInteraction(book._id, 'view', {
      source: 'top-recommendations',
      mmr_enabled: mmrEnabled,
    });
    navigate(`/books/${book._id}`);
  };

  if (loading) {
    return (
      <Box sx={pageStyles.sectionContainer}>
        <LoadingSkeleton.Section cardCount={6} />
      </Box>
    );
  }

  if (!books || books.length === 0) {
    return null;
  }

  const topBooks = books.slice(0, 8);

  return (
    <Box sx={pageStyles.sectionContainer}>
      <SectionTitle
        icon={AutoAwesome}
        title="Dla Ciebie - Nasze najlepsze propozycje"
        subtitle="Zbalansowane pod kątem trafności i różnorodności dzięki algorytmowi LightGCN + MMR"
      />

      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <Chip
          icon={<Science sx={{ fontSize: 14 }} />}
          label={mmrEnabled ? 'LightGCN + MMR re-ranking' : 'Tylko LightGCN'}
          size="small"
          sx={{
            bgcolor: 'rgba(102, 192, 244, 0.2)',
            color: COLORS.accent,
            border: `1px solid ${COLORS.accent}`,
          }}
        />
        <Chip
          label="Personalizowane"
          size="small"
          sx={{
            bgcolor: 'rgba(255, 193, 7, 0.2)',
            color: COLORS.goldAccent,
            border: `1px solid ${COLORS.goldAccent}`,
          }}
        />
      </Box>

      <HorizontalBookScroll
        books={topBooks}
        onBookClick={handleBookClick}
        showScore={true}
        showReason={true}
        interactionSource="top-recommendations"
      />
    </Box>
  );
};

export default TopRecommendations;
