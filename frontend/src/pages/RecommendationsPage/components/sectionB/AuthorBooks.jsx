/**
 * AuthorBooks.jsx - SEKCJA B: "Inne dzieła autora..."
 *
 * Z wykorzystaniem metadanych, ale z rankingiem personalizowanym
 * (które książki tego autora najbardziej pasują do Twojego profilu)
 */

import React from 'react';
import { Box, Chip, Paper, Typography, Avatar } from '@mui/material';
import { Person, AutoStories } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import SectionTitle from '../shared/SectionTitle';
import HorizontalBookScroll from '../shared/HorizontalBookScroll';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import { COLORS, pageStyles } from '../../styles/theme';
import { recommendationsAPI } from '../../../../services/api';

const AuthorBooks = ({ authorSections, loading }) => {
  const navigate = useNavigate();

  const handleBookClick = async (book, author) => {
    await recommendationsAPI.reportInteraction(book._id, 'view', {
      source: 'author-books',
      author: author,
    });
    navigate(`/books/${book._id}`);
  };

  const handleSeeMore = (author) => {
    navigate(`/books?author=${encodeURIComponent(author)}`);
  };

  if (loading) {
    return (
      <Box sx={pageStyles.sectionContainer}>
        <LoadingSkeleton.Section cardCount={4} />
      </Box>
    );
  }

  if (!authorSections || authorSections.length === 0) {
    return null;
  }

  return (
    <>
      {authorSections.map((section, idx) => {
        const { author, books } = section;

        if (!books || books.length === 0) return null;

        // Inicjały autora do avatara
        const initials = author
          .split(' ')
          .map((n) => n[0])
          .join('')
          .toUpperCase()
          .slice(0, 2);

        return (
          <Box key={author || idx} sx={pageStyles.sectionContainer}>
            {/* Section Title z avatarem */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
              <Avatar
                sx={{
                  bgcolor: COLORS.accent,
                  color: COLORS.bgDark,
                  width: 50,
                  height: 50,
                  fontWeight: 600,
                }}
              >
                {initials}
              </Avatar>
              <Box sx={{ flex: 1 }}>
                <SectionTitle
                  icon={Person}
                  title={`Inne dzieła autora: ${author}`}
                  actionLabel="Zobacz wszystkie"
                  onAction={() => handleSeeMore(author)}
                  subtitle="Personalizowane dla Ciebie"
                />
              </Box>
            </Box>

            {/* Author Stats */}
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <Chip
                icon={<AutoStories sx={{ fontSize: 14 }} />}
                label={`${books.length} książek dostępnych`}
                size="small"
                sx={{
                  bgcolor: 'rgba(76, 175, 80, 0.2)',
                  color: COLORS.successGreen,
                  border: `1px solid ${COLORS.successGreen}`,
                }}
              />
            </Box>

            {/* Books Carousel */}
            <HorizontalBookScroll
              books={books.slice(0, 10)}
              onBookClick={(book) => handleBookClick(book, author)}
              showScore={true}
              showReason={false}
              interactionSource="author-books"
            />

            {/* Explanation - tylko dla pierwszej sekcji */}
            {idx === 0 && (
              <Paper
                sx={{
                  mt: 2,
                  p: 1.5,
                  background: 'rgba(76, 175, 80, 0.05)',
                  border: `1px solid ${COLORS.bgMedium}`,
                  borderRadius: 1,
                }}
              >
                <Typography variant="caption" sx={{ color: COLORS.textSecondary }}>
                  📚 <strong>Jak to działa?</strong> Wybieramy książki tego samego autora, którego
                  już lubisz, a następnie używamy LightGCN do spersonalizowanego rankingu - które z
                  jego dzieł najbardziej pasują do Twojego profilu czytelniczego.
                </Typography>
              </Paper>
            )}
          </Box>
        );
      })}
    </>
  );
};

export default AuthorBooks;
