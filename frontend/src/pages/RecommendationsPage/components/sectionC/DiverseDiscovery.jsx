import React from 'react';
import { Box, Chip, Typography, LinearProgress } from '@mui/material';
import { Explore, Casino, AutoAwesome } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import SectionTitle from '../shared/SectionTitle';
import HorizontalBookScroll from '../shared/HorizontalBookScroll';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import { COLORS, pageStyles } from '../../styles/theme';
import { recommendationsAPI } from '../../../../services/api';

const DiverseDiscovery = ({ books, diversityScore, loading }) => {
  const navigate = useNavigate();

  const handleBookClick = async (book) => {
    await recommendationsAPI.reportInteraction(book._id, 'view', {
      source: 'diverse-discovery',
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

  const diversity = diversityScore || 0.75;

  return (
    <Box sx={pageStyles.sectionContainer}>
      <SectionTitle
        icon={Explore}
        title="Odkryj coś nowego - poza Twoją bańką"
        subtitle="Specjalnie dla Ciebie wybraliśmy różnorodne pozycje"
      />

      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
          <Chip
            icon={<Casino sx={{ fontSize: 14 }} />}
            label="Wysoka różnorodność (MMR λ ≈ 0.3)"
            size="small"
            sx={{
              bgcolor: 'rgba(255, 87, 34, 0.2)',
              color: '#ff8a65',
              border: '1px solid #ff8a65',
            }}
          />
          <Chip
            icon={<AutoAwesome sx={{ fontSize: 14 }} />}
            label="Eksploracja nowych gatunków"
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
              Poziom różnorodności
            </Typography>
            <Typography variant="caption" sx={{ color: COLORS.accent, fontWeight: 600 }}>
              {Math.round(diversity * 100)}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={diversity * 100}
            sx={{
              height: 6,
              borderRadius: 3,
              bgcolor: COLORS.bgDark,
              '& .MuiLinearProgress-bar': {
                bgcolor: COLORS.accent,
              },
            }}
          />
        </Box>
      </Box>

      <HorizontalBookScroll
        books={books.slice(0, 8)}
        onBookClick={handleBookClick}
        showScore={false}
        showReason={true}
        interactionSource="diverse-discovery"
      />
    </Box>
  );
};

export default DiverseDiscovery;
