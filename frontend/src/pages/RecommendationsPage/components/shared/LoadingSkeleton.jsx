
import React from 'react';
import { Box, Skeleton } from '@mui/material';
import { COLORS } from '../../styles/theme';

export const BookCardSkeleton = ({ compact = false }) => (
  <Skeleton
    variant="rectangular"
    width={compact ? 150 : 180}
    height={compact ? 200 : 280}
    sx={{
      borderRadius: 1,
      bgcolor: COLORS.bgMedium,
      flexShrink: 0,
    }}
  />
);

export const HorizontalScrollSkeleton = ({ count = 5, compact = false }) => (
  <Box sx={{ display: 'flex', gap: 2, overflow: 'hidden' }}>
    {Array.from({ length: count }).map((_, i) => (
      <BookCardSkeleton key={i} compact={compact} />
    ))}
  </Box>
);

export const SectionTitleSkeleton = () => (
  <Skeleton
    width={300}
    height={24}
    sx={{
      bgcolor: COLORS.bgMedium,
      mb: 2,
    }}
  />
);

export const FeaturedCarouselSkeleton = () => (
  <Box sx={{ height: 400, position: 'relative', mb: 6 }}>
    <Skeleton
      variant="rectangular"
      width="100%"
      height={400}
      sx={{
        bgcolor: COLORS.bgMedium,
        borderRadius: 2,
      }}
    />
  </Box>
);

export const SectionSkeleton = ({ showTitle = true, cardCount = 4, compact = false }) => (
  <Box sx={{ mb: 5 }}>
    {showTitle && <SectionTitleSkeleton />}
    <HorizontalScrollSkeleton count={cardCount} compact={compact} />
  </Box>
);

const LoadingSkeleton = {
  BookCard: BookCardSkeleton,
  HorizontalScroll: HorizontalScrollSkeleton,
  SectionTitle: SectionTitleSkeleton,
  FeaturedCarousel: FeaturedCarouselSkeleton,
  Section: SectionSkeleton,
};

export default LoadingSkeleton;
