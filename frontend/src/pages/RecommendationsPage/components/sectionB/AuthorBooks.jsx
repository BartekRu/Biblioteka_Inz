/**
 * AuthorBooks.jsx - SEKCJA B: "Inne dzieła autora..."
 *
 * Z wykorzystaniem metadanych, ale z rankingiem personalizowanym
 * (które książki tego autora najbardziej pasują do Twojego profilu)
 */

import React from 'react';
import { Box, Chip, Avatar } from '@mui/material';
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
      {authorSections.slice(0, 1).map((section, idx) => {
        const { author, books } = section;

        if (!books || books.length === 0) return null;

        const initials = author
          .split(' ')
          .map((n) => n[0])
          .join('')
          .toUpperCase()
          .slice(0, 2);

        return (
          <Box key={author || idx} sx={pageStyles.sectionContainer}>
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

            <HorizontalBookScroll
              books={books.slice(0, 20)}
              onBookClick={(book) => handleBookClick(book, author)}
              showScore={true}
              showReason={false}
              interactionSource="author-books"
            />
          </Box>
        );
      })}
    </>
  );
};

export default AuthorBooks;
