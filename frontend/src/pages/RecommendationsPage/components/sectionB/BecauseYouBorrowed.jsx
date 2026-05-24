

import React from 'react';
import { Box, Typography } from '@mui/material';
import { MenuBook } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import HorizontalBookScroll from '../shared/HorizontalBookScroll';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import { COLORS, pageStyles } from '../../styles/theme';
import { recommendationsAPI } from '../../../../services/api';
import { getBookImage } from '../../utils/bookHelpers';

const BecauseYouBorrowed = ({ sections, loading }) => {
  const navigate = useNavigate();

  const handleBookClick = async (book, sourceBookId) => {
    await recommendationsAPI.reportInteraction(book._id, 'view', {
      source: 'because-borrowed',
      source_book_id: sourceBookId,
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

  if (!sections || sections.length === 0) {
    return null;
  }

  return (
    <>
      {sections.map((section, idx) => {
        const sourceBook = section.sourceBook;
        const recommendations = section.recommendations || [];

        if (!sourceBook || recommendations.length === 0) return null;

        return (
          <Box key={sourceBook._id || idx} sx={pageStyles.sectionContainer}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
              <Box
                component="img"
                src={getBookImage(sourceBook)}
                alt={sourceBook.title}
                sx={{
                  width: 50,
                  height: 70,
                  objectFit: 'cover',
                  borderRadius: 1,
                  border: `2px solid ${COLORS.accent}`,
                }}
              />
              <Box sx={{ flex: 1 }}>
                <Typography sx={pageStyles.sectionTitle}>
                  <MenuBook sx={{ color: COLORS.accent }} />
                  Ponieważ wypożyczyłeś{' '}
                  <Box
                    component="span"
                    sx={{ color: 'white', fontWeight: 600, textTransform: 'none' }}
                  >
                    "{sourceBook.title}"
                  </Box>
                </Typography>
                <Typography variant="caption" sx={{ color: COLORS.textSecondary, ml: 4 }}>
                  Podobne książki w przestrzeni embeddingów LightGCN
                </Typography>
              </Box>
            </Box>

            <HorizontalBookScroll
              books={recommendations}
              onBookClick={(book) => handleBookClick(book, sourceBook._id)}
              showScore={true}
              showReason={false}
              interactionSource="because-borrowed"
            />
          </Box>
        );
      })}
    </>
  );
};

export default BecauseYouBorrowed;
