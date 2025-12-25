/**
 * index.js - Barrel exports for easier imports
 *
 * Instead of:
 *   import BookCard from './components/shared/BookCard';
 *   import SectionTitle from './components/shared/SectionTitle';
 *
 * Use:
 *   import { BookCard, SectionTitle } from './components/shared';
 */

// ============================================================================
// SHARED COMPONENTS
// ============================================================================

export { default as BookCard } from './components/shared/BookCard';
export { default as SectionTitle } from './components/shared/SectionTitle';
export { default as HorizontalBookScroll } from './components/shared/HorizontalBookScroll';
export {
  default as LoadingSkeleton,
  BookCardSkeleton,
  HorizontalScrollSkeleton,
  SectionTitleSkeleton,
  FeaturedCarouselSkeleton,
  SectionSkeleton,
} from './components/shared/LoadingSkeleton';

// ============================================================================
// CONTROLS
// ============================================================================

export { default as MMRControlPanel } from './components/controls/MMRControlPanel';

// ============================================================================
// SECTION A
// ============================================================================

export { default as TopRecommendations } from './components/sectionA/TopRecommendations';

// ============================================================================
// SECTION B
// ============================================================================

export { default as BecauseYouBorrowed } from './components/sectionB/BecauseYouBorrowed';
export { default as GenreRecommendations } from './components/sectionB/GenreRecommendations';
export { default as AuthorBooks } from './components/sectionB/AuthorBooks';
export { default as SimilarReaders } from './components/sectionB/SimilarReaders';

// ============================================================================
// SECTION C
// ============================================================================

export { default as DiverseDiscovery } from './components/sectionC/DiverseDiscovery';
export { default as NewArrivals } from './components/sectionC/NewArrivals';
export { default as LibrarianPicks } from './components/sectionC/LibrarianPicks';

// ============================================================================
// STYLES & UTILS
// ============================================================================

export { COLORS, pageStyles, animations } from './styles/theme';
export * from './utils/bookHelpers';

// ============================================================================
// MAIN PAGE
// ============================================================================

export { default as RecommendationsPage } from './RecommendationsPage';
export { default } from './RecommendationsPage';
