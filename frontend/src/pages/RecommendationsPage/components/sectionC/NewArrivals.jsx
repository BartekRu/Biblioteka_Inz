import React from 'react';
import { Box, Chip, Paper, Typography, Badge } from '@mui/material';
import { FiberNew, TrendingUp, Science } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import SectionTitle from '../shared/SectionTitle';
import HorizontalBookScroll from '../shared/HorizontalBookScroll';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import { COLORS, pageStyles } from '../../styles/theme';
import { recommendationsAPI } from '../../../../services/api';

const NewArrivals = ({ books, loading }) => {
  const navigate = useNavigate();

  const handleBookClick = async (book) => {
    await recommendationsAPI.reportInteraction(book._id, 'view', {
      source: 'new-arrivals',
    });
    navigate(`/books/${book._id}`);
  };

  const handleSeeAll = () => {
    navigate('/books?sort=newest');
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

  const recentCount = books.filter((book) => {
    if (!book.addedDate) return false;
    const addedDate = new Date(book.addedDate);
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return addedDate > weekAgo;
  }).length;

  return (
    <Box sx={pageStyles.sectionContainer}>
      <SectionTitle
        icon={FiberNew}
        title="Nowości w bibliotece, które mogą Ci się spodobać"
        actionLabel="Zobacz wszystkie nowości"
        onAction={handleSeeAll}
        subtitle="Świeże tytuły dopasowane do Twoich preferencji"
      />

      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <Badge badgeContent={recentCount || books.length} color="error" max={99}>
          <Chip
            icon={<FiberNew sx={{ fontSize: 14 }} />}
            label="Nowe książki"
            size="small"
            sx={{
              bgcolor: 'rgba(76, 175, 80, 0.2)',
              color: COLORS.successGreen,
              border: `1px solid ${COLORS.successGreen}`,
            }}
          />
        </Badge>
        <Chip
          icon={<Science sx={{ fontSize: 14 }} />}
          label="Cold-start handling"
          size="small"
          sx={{
            bgcolor: 'rgba(102, 192, 244, 0.2)',
            color: COLORS.accent,
            border: `1px solid ${COLORS.accent}`,
          }}
        />
      </Box>

      <HorizontalBookScroll
        books={books.slice(0, 10)}
        onBookClick={handleBookClick}
        showScore={true}
        showReason={true}
        interactionSource="new-arrivals"
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
          🆕 <strong>Jak to działa?</strong> To tzw. "cold-start problem" - nowe książki nie mają
          jeszcze historii wypożyczeń. System analizuje metadane (gatunek, autor, opis) i porównuje
          je z Twoim profilem czytelniczym, aby znaleźć najbardziej pasujące nowości.
        </Typography>
        <Typography variant="caption" sx={{ color: COLORS.textSecondary, fontStyle: 'italic' }}>
          💡 Im więcej osób wypożyczy te książki, tym lepsze będą rekomendacje oparte na LightGCN!
        </Typography>
      </Paper>
    </Box>
  );
};

export default NewArrivals;
