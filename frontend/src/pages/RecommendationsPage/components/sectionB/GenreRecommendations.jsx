/**
 * GenreRecommendations.jsx - POPRAWIONA WERSJA
 * SEKCJA B: "Dla miłośników gatunku..."
 */

import React, { useEffect } from 'react';
import { Box, Chip, Paper, Typography, Alert } from '@mui/material';
import { Category, FilterList, Warning } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import SectionTitle from '../shared/SectionTitle';
import HorizontalBookScroll from '../shared/HorizontalBookScroll';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import { COLORS, pageStyles } from '../../styles/theme';
import { recommendationsAPI } from '../../../../services/api';

const GenreRecommendations = ({ genreSections, loading, error }) => {
  const navigate = useNavigate();

  // 🔍 DEBUG: Log when component mounts and when data changes
  useEffect(() => {
    console.log('🎯 GenreRecommendations mounted/updated:', {
      loading,
      error,
      sectionsCount: genreSections?.length || 0,
      sections: genreSections,
    });
  }, [genreSections, loading, error]);

  const handleBookClick = async (book, genre) => {
    console.log('📖 Book clicked:', { book: book.title, genre });

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
    console.log('🔍 See more clicked for genre:', genre);
    navigate(`/books?genre=${genre}`);
  };

  // Loading state
  if (loading) {
    console.log('⏳ GenreRecommendations: Loading...');
    return (
      <Box sx={pageStyles.sectionContainer}>
        <LoadingSkeleton.Section cardCount={4} />
      </Box>
    );
  }

  // Error state
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

  // Empty data state
  if (!genreSections || genreSections.length === 0) {
    console.warn('⚠️ GenreRecommendations: No sections to display');

    // Pokaż info zamiast nic nie renderować
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

  console.log(`✅ GenreRecommendations: Rendering ${genreSections.length} sections`);

  return (
    <>
      {genreSections.map((section, idx) => {
        const { genre, books, user_preference_score } = section;

        // Validation
        if (!genre) {
          console.warn('⚠️ Section without genre:', section);
          return null;
        }

        if (!books || books.length === 0) {
          console.warn(`⚠️ No books for genre: ${genre}`);
          return null;
        }

        console.log(`📚 Rendering section for genre: ${genre} (${books.length} books)`);

        return (
          <Box key={genre || idx} sx={pageStyles.sectionContainer}>
            {/* Section Title */}
            <SectionTitle
              icon={Category}
              title={`Dla miłośników gatunku: ${genre}`}
              actionLabel="Zobacz wszystkie"
              onAction={() => handleSeeMore(genre)}
              subtitle="Filtrowane przez gatunek + personalizacja LightGCN"
            />

            {/* Genre Badge */}
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

            {/* Books Carousel */}
            <HorizontalBookScroll
              books={books.slice(0, 10)}
              onBookClick={(book) => handleBookClick(book, genre)}
              showScore={true}
              showReason={false}
              interactionSource="genre-recommendations"
            />

            {/* Explanation - tylko dla pierwszej sekcji */}
            {idx === 0 && (
              <Paper
                sx={{
                  mt: 2,
                  p: 1.5,
                  background: 'rgba(102, 192, 244, 0.05)',
                  border: `1px solid ${COLORS.bgMedium}`,
                  borderRadius: 1,
                }}
              >
                <Typography variant="caption" sx={{ color: COLORS.textSecondary }}>
                  🎯 <strong>Jak to działa?</strong> Najpierw filtrujemy książki według Twojego
                  ulubionego gatunku, a następnie używamy embeddingów z LightGCN, aby wybrać te,
                  które najbardziej pasują do Twojego profilu czytelniczego.
                </Typography>
              </Paper>
            )}
          </Box>
        );
      })}
    </>
  );
};

export default GenreRecommendations;
