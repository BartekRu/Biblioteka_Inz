/**
 * GenreRecommendations.jsx - SEKCJA B: "Dla miłośników gatunku..."
 *
 * Rekomendacje filtrowane przez gatunek, ale rerankowane personalizacją z LightGCN
 */

import React from 'react';
import { Box, Chip, Paper, Typography } from '@mui/material';
import { Category, FilterList } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import SectionTitle from '../shared/SectionTitle';
import HorizontalBookScroll from '../shared/HorizontalBookScroll';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import { COLORS, pageStyles } from '../../styles/theme';
import { recommendationsAPI } from '../../../../services/api';

const GenreRecommendations = ({ genreSections, loading }) => {
  const navigate = useNavigate();

  const handleBookClick = async (book, genre) => {
    await recommendationsAPI.reportInteraction(book._id, 'view', {
      source: 'genre-recommendations',
      genre: genre,
    });
    navigate(`/books/${book._id}`);
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

  if (!genreSections || genreSections.length === 0) {
    return null;
  }

  return (
    <>
      {genreSections.map((section, idx) => {
        const { genre, books } = section;

        if (!books || books.length === 0) return null;

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
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
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
