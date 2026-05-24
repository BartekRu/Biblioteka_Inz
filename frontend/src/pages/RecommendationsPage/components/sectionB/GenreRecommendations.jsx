import React from 'react';
import { Box, Chip, Typography, Alert } from '@mui/material';
import { Category, FilterList, Warning } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import SectionTitle from '../shared/SectionTitle';
import HorizontalBookScroll from '../shared/HorizontalBookScroll';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import { COLORS, pageStyles } from '../../styles/theme';
import { recommendationsAPI } from '../../../../services/api';

const GenreRecommendations = ({ genreSections, loading, error }) => {
  const navigate = useNavigate();

  const handleBookClick = async (book, genre) => {
    try {
      await recommendationsAPI.reportInteraction(book._id, 'view', {
        source: 'genre-recommendations',
        genre: genre,
      });
      navigate(`/books/${book._id}`);
    } catch (err) {
      console.error('❌ Failed to report interaction:', err);
      navigate(`/books/${book._id}`);
    }
  };

  const handleSeeMore = (genre) => {
    navigate(`/books?genre=${genre}`);
  };

  if (loading) {
    return (
      <Box sx={pageStyles.sectionContainer}>
        <LoadingSkeleton.Section cardCount={4} />
      </Box>
    );
  }

  if (error) {
    console.error('❌ GenreRecommendations: Error state:', error);
    return (
      <Box sx={pageStyles.sectionContainer}>
        <Alert severity="error" icon={<Warning />}>
          <Typography variant="body2">
            Nie udało się załadować rekomendacji według gatunku: {error.message || 'Nieznany błąd'}
          </Typography>
        </Alert>
      </Box>
    );
  }

  if (!genreSections || genreSections.length === 0) {
    console.warn('⚠️ GenreRecommendations: No sections to display');

    return (
      <Box sx={pageStyles.sectionContainer}>
        <Alert severity="info" icon={<Category />}>
          <Typography variant="body2">
            Brak rekomendacji według gatunku. Wypożycz kilka książek, aby otrzymać personalizowane
            sugestie!
          </Typography>
        </Alert>
      </Box>
    );
  }

  return (
    <>
      {genreSections.slice(0, 2).map((section, idx) => {
        const { genre, books, user_preference_score } = section;

        if (!genre) {
          console.warn('⚠️ Section without genre:', section);
          return null;
        }

        if (!books || books.length === 0) {
          console.warn(`⚠️ No books for genre: ${genre}`);
          return null;
        }

        return (
          <Box key={genre || idx} sx={pageStyles.sectionContainer}>
            <SectionTitle
              icon={Category}
              title={`Dla miłośników gatunku: ${genre}`}
              actionLabel="Zobacz wszystkie"
              onAction={() => handleSeeMore(genre)}
              subtitle="Filtrowane przez gatunek + personalizacja LightGCN"
            />

            <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
              <Chip
                icon={<FilterList sx={{ fontSize: 14 }} />}
                label={`${books.length} książek w kategorii`}
                size="small"
                sx={{
                  bgcolor: 'rgba(102, 192, 244, 0.2)',
                  color: COLORS.accent,
                  border: `1px solid ${COLORS.accent}`,
                }}
              />

              {user_preference_score && (
                <Chip
                  label={`Dopasowanie: ${Math.round(user_preference_score * 100)}%`}
                  size="small"
                  sx={{
                    bgcolor: 'rgba(102, 192, 244, 0.1)',
                    color: COLORS.textSecondary,
                  }}
                />
              )}
            </Box>

            <HorizontalBookScroll
              books={books.slice(0, 10)}
              onBookClick={(book) => handleBookClick(book, genre)}
              showScore={true}
              showReason={false}
              interactionSource="genre-recommendations"
            />
          </Box>
        );
      })}
    </>
  );
};

export default GenreRecommendations;
