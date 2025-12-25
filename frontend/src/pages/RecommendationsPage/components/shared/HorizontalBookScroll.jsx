/**
 * HorizontalBookScroll.jsx - Horizontal scrollable book list with navigation
 */

import React, { useRef } from 'react';
import { Box, IconButton } from '@mui/material';
import { ChevronLeft, ChevronRight } from '@mui/icons-material';
import { pageStyles } from '../../styles/theme';
import BookCard from './BookCard';

const HorizontalBookScroll = ({
  books,
  onBookClick,
  showScore = true,
  showReason = false,
  compact = false,
  interactionSource = 'horizontal-scroll',
}) => {
  const scrollRef = useRef(null);

  const scroll = (direction) => {
    if (scrollRef.current) {
      const scrollAmount = compact ? 200 : 250;
      scrollRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      });
    }
  };

  if (!books || books.length === 0) {
    return null;
  }

  return (
    <Box sx={{ position: 'relative' }}>
      {/* Scrollable Container */}
      <Box
        ref={scrollRef}
        sx={{
          display: 'flex',
          gap: 2,
          overflowX: 'auto',
          pb: 2,
          scrollbarWidth: 'none',
          '&::-webkit-scrollbar': { display: 'none' },
        }}
      >
        {books.map((book) => (
          <BookCard
            key={book._id}
            book={book}
            onClick={() => onBookClick(book)}
            showScore={showScore}
            showReason={showReason}
            compact={compact}
            interactionSource={interactionSource}
          />
        ))}
      </Box>

      {/* Navigation Buttons */}
      {books.length > 4 && (
        <>
          <IconButton
            onClick={() => scroll('left')}
            sx={{
              ...pageStyles.navButton,
              left: -20,
              top: '45%',
            }}
            size="small"
          >
            <ChevronLeft />
          </IconButton>
          <IconButton
            onClick={() => scroll('right')}
            sx={{
              ...pageStyles.navButton,
              right: -20,
              top: '45%',
            }}
            size="small"
          >
            <ChevronRight />
          </IconButton>
        </>
      )}
    </Box>
  );
};

export default HorizontalBookScroll;
