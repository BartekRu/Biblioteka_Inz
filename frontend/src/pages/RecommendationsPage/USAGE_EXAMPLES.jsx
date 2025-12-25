/**
 * USAGE_EXAMPLES.jsx - Przykłady użycia komponentów
 *
 * Ten plik pokazuje jak używać każdego komponentu osobno
 * oraz jak łączyć je w większe struktury
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';

// ============================================================================
// PRZYKŁAD 1: Użycie BookCard
// ============================================================================

import BookCard from './components/shared/BookCard';
import { recommendationsAPI } from '../../services/api';

function BookCardExample() {
  const navigate = useNavigate();

  const exampleBook = {
    _id: '507f1f77bcf86cd799439011',
    title: 'The Name of the Wind',
    author: 'Patrick Rothfuss',
    genres: ['Fantasy', 'Adventure'],
    description: 'A tale of magic, music, and mystery...',
    coverImage: 'https://example.com/cover.jpg',
    averageRating: 4.5,
    reviewCount: 2500,
    available: true,
    matchScore: 0.95,
    recommendationReason: 'Dopasowane do Twoich preferencji',
    onWishlist: false,
  };

  const handleBookClick = async () => {
    // Report interaction
    await recommendationsAPI.reportInteraction(exampleBook._id, 'view', {
      source: 'my-section',
    });

    // Navigate to details
    navigate(`/books/${exampleBook._id}`);
  };

  return (
    <BookCard
      book={exampleBook}
      onClick={handleBookClick}
      showScore={true}
      showReason={true}
      compact={false}
      interactionSource="example-section"
    />
  );
}

// ============================================================================
// PRZYKŁAD 2: Użycie HorizontalBookScroll
// ============================================================================

import HorizontalBookScroll from './components/shared/HorizontalBookScroll';

function HorizontalScrollExample() {
  const navigate = useNavigate();

  const books = [
    // ... array of books
  ];

  const handleBookClick = async (book) => {
    await recommendationsAPI.reportInteraction(book._id, 'view', {
      source: 'scroll-section',
    });
    navigate(`/books/${book._id}`);
  };

  return (
    <HorizontalBookScroll
      books={books}
      onBookClick={handleBookClick}
      showScore={true}
      showReason={false}
      interactionSource="my-scroll"
    />
  );
}

// ============================================================================
// PRZYKŁAD 3: Użycie SectionTitle
// ============================================================================

import SectionTitle from './components/shared/SectionTitle';
import { AutoAwesome } from '@mui/icons-material';

function SectionTitleExample() {
  const navigate = useNavigate();

  return (
    <>
      {/* Prosty tytuł */}
      <SectionTitle icon={AutoAwesome} title="Rekomendacje dla Ciebie" />

      {/* Z podtytułem */}
      <SectionTitle
        icon={AutoAwesome}
        title="Rekomendacje dla Ciebie"
        subtitle="Spersonalizowane przez AI"
      />

      {/* Z akcją */}
      <SectionTitle
        icon={AutoAwesome}
        title="Rekomendacje dla Ciebie"
        subtitle="Spersonalizowane przez AI"
        actionLabel="Zobacz wszystkie"
        onAction={() => navigate('/all-recommendations')}
      />
    </>
  );
}

// ============================================================================
// PRZYKŁAD 4: Użycie LoadingSkeleton
// ============================================================================

import LoadingSkeleton from './components/shared/LoadingSkeleton';

function LoadingExample({ loading }) {
  if (loading) {
    return (
      <>
        {/* Single card skeleton */}
        <LoadingSkeleton.BookCard />

        {/* Compact card */}
        <LoadingSkeleton.BookCard compact={true} />

        {/* Horizontal scroll skeleton */}
        <LoadingSkeleton.HorizontalScroll count={5} />

        {/* Section title skeleton */}
        <LoadingSkeleton.SectionTitle />

        {/* Complete section skeleton */}
        <LoadingSkeleton.Section showTitle={true} cardCount={4} />
      </>
    );
  }

  return <div>Content loaded!</div>;
}

// ============================================================================
// PRZYKŁAD 5: Kompletna sekcja rekomendacji
// ============================================================================

import { Box } from '@mui/material';
import { pageStyles } from './styles/theme';

function CompleteSection() {
  const navigate = useNavigate();
  const [loading, setLoading] = React.useState(true);
  const [books, setBooks] = React.useState([]);

  React.useEffect(() => {
    async function fetchData() {
      try {
        const response = await recommendationsAPI.getUserLightGCN(10);
        setBooks(response.data.recommendations || []);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const handleBookClick = async (book) => {
    await recommendationsAPI.reportInteraction(book._id, 'view', {
      source: 'complete-section',
    });
    navigate(`/books/${book._id}`);
  };

  if (loading) {
    return <LoadingSkeleton.Section />;
  }

  if (!books || books.length === 0) {
    return null;
  }

  return (
    <Box sx={pageStyles.sectionContainer}>
      <SectionTitle
        icon={AutoAwesome}
        title="Twoje rekomendacje"
        subtitle="Spersonalizowane przez LightGCN"
        actionLabel="Zobacz wszystkie"
        onAction={() => navigate('/all')}
      />

      <HorizontalBookScroll
        books={books}
        onBookClick={handleBookClick}
        showScore={true}
        showReason={true}
        interactionSource="complete-section"
      />
    </Box>
  );
}

// ============================================================================
// PRZYKŁAD 6: Używanie MMRControlPanel
// ============================================================================

import MMRControlPanel from './components/controls/MMRControlPanel';

function MMRExample() {
  const [mmrEnabled, setMmrEnabled] = React.useState(true);
  const [lambdaValue, setLambdaValue] = React.useState(0.7);
  const [authorLimit, setAuthorLimit] = React.useState(true);
  const [diversityMetrics, setDiversityMetrics] = React.useState({
    unique_genres: 8,
    unique_authors: 15,
    avg_pairwise_dissimilarity: 0.67,
  });

  return (
    <MMRControlPanel
      mmrEnabled={mmrEnabled}
      onMmrToggle={setMmrEnabled}
      lambdaValue={lambdaValue}
      onLambdaChange={setLambdaValue}
      authorLimit={authorLimit}
      onAuthorLimitToggle={setAuthorLimit}
      maxPerAuthor={2}
      diversityMetrics={diversityMetrics}
      loading={false}
    />
  );
}

// ============================================================================
// PRZYKŁAD 7: Użycie komponentów sekcji
// ============================================================================

import TopRecommendations from './components/sectionA/TopRecommendations';
import BecauseYouBorrowed from './components/sectionB/BecauseYouBorrowed';
import GenreRecommendations from './components/sectionB/GenreRecommendations';
import AuthorBooks from './components/sectionB/AuthorBooks';
import SimilarReaders from './components/sectionB/SimilarReaders';
import DiverseDiscovery from './components/sectionC/DiverseDiscovery';
import NewArrivals from './components/sectionC/NewArrivals';
import LibrarianPicks from './components/sectionC/LibrarianPicks';

function SectionsExample() {
  const [loading, setLoading] = React.useState(false);
  const [data, setData] = React.useState({
    topRecs: [],
    becauseSections: [],
    genreSections: [],
    authorSections: [],
    similarReaders: { books: [], similar_user_count: 0 },
    diverse: [],
    newArrivals: [],
    librarianPicks: { books: [], curator: null },
  });

  return (
    <div>
      {/* SEKCJA A */}
      <TopRecommendations books={data.topRecs} loading={loading} mmrEnabled={true} />

      {/* SEKCJA B */}
      <BecauseYouBorrowed sections={data.becauseSections} loading={loading} />

      <GenreRecommendations genreSections={data.genreSections} loading={loading} />

      <AuthorBooks authorSections={data.authorSections} loading={loading} />

      <SimilarReaders
        books={data.similarReaders.books}
        similarUserCount={data.similarReaders.similar_user_count}
        loading={loading}
      />

      {/* SEKCJA C */}
      <DiverseDiscovery books={data.diverse} diversityScore={0.8} loading={loading} />

      <NewArrivals books={data.newArrivals} loading={loading} />

      <LibrarianPicks
        books={data.librarianPicks.books}
        curator={data.librarianPicks.curator}
        loading={loading}
      />
    </div>
  );
}

// ============================================================================
// PRZYKŁAD 8: Custom hook do zarządzania rekomendacjami
// ============================================================================

function useRecommendationsData(mmrSettings) {
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [data, setData] = React.useState({
    topRecommendations: [],
    diversityMetrics: null,
    becauseSections: [],
    genreSections: [],
    authorSections: [],
    similarReaders: { books: [], similar_user_count: 0 },
    diverse: [],
    newArrivals: [],
    librarianPicks: { books: [], curator: null },
  });

  const fetchData = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [topRes, becauseRes, genreRes, authorRes, similarRes, diverseRes, newRes, libRes] =
        await Promise.allSettled([
          recommendationsAPI.getUserLightGCN(
            30,
            0,
            mmrSettings.enabled,
            mmrSettings.lambda,
            mmrSettings.authorLimit,
            2
          ),
          recommendationsAPI.getBecauseYouBorrowed(),
          recommendationsAPI.getGenreRecommendations(),
          recommendationsAPI.getAuthorRecommendations(),
          recommendationsAPI.getSimilarReadersBooks(),
          recommendationsAPI.getUserLightGCN(10, 0, true, 0.3, true, 2),
          recommendationsAPI.getNewArrivals(),
          recommendationsAPI.getLibrarianPicks(),
        ]);

      // Process results
      const newData = { ...data };

      if (topRes.status === 'fulfilled') {
        const responseData = topRes.value.data;
        newData.topRecommendations = responseData.recommendations || [];
        newData.diversityMetrics = responseData.metadata?.diversity_metrics;
      }

      if (becauseRes.status === 'fulfilled') {
        newData.becauseSections = becauseRes.value.data || [];
      }

      // ... process other results

      setData(newData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [mmrSettings]);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { loading, error, data, refetch: fetchData };
}

// Użycie custom hook:
function MyRecommendationsPage() {
  const [mmrSettings, setMmrSettings] = React.useState({
    enabled: true,
    lambda: 0.7,
    authorLimit: true,
  });

  const { loading, error, data, refetch } = useRecommendationsData(mmrSettings);

  return (
    <div>
      <MMRControlPanel
        mmrEnabled={mmrSettings.enabled}
        onMmrToggle={(enabled) => setMmrSettings({ ...mmrSettings, enabled })}
        lambdaValue={mmrSettings.lambda}
        onLambdaChange={(lambda) => setMmrSettings({ ...mmrSettings, lambda })}
        // ... other props
      />

      {error && <div>Error: {error}</div>}

      <TopRecommendations books={data.topRecommendations} loading={loading} mmrEnabled={true} />

      {/* ... other sections */}
    </div>
  );
}

// ============================================================================
// PRZYKŁAD 9: Używanie utils/bookHelpers
// ============================================================================

import {
  getBookImage,
  getBookGenres,
  getBookRating,
  isBookAvailable,
  getMatchScorePercent,
  truncateText,
  getRecommendationReason,
  sortByMatchScore,
  groupByAuthor,
  groupByGenre,
} from './utils/bookHelpers';

function BookHelpersExample() {
  const book = {
    _id: '1',
    title: 'Example Book',
    coverImage: null, // will use fallback
    genres: ['Fantasy', 'Adventure'],
    average_rating: 4.5, // note: different field name
    available_copies: 3,
    matchScore: 0.95,
    description: 'A very long description that needs to be truncated...',
  };

  // Get book image with automatic fallback
  const image = getBookImage(book); // → '/default-book-cover.jpg'

  // Get genres (handles different field names)
  const genres = getBookGenres(book); // → ['Fantasy', 'Adventure']

  // Get rating (handles different field names)
  const rating = getBookRating(book); // → 4.5

  // Check availability
  const available = isBookAvailable(book); // → true

  // Get match score as percentage
  const matchPercent = getMatchScorePercent(book); // → 95

  // Truncate description
  const shortDesc = truncateText(book.description, 50); // → "A very long description that needs to be trun..."

  // Get recommendation reason
  const reason = getRecommendationReason(book); // → 'Polecane przez AI'

  // Sort books by match score
  const books = [
    /* ... */
  ];
  const sorted = sortByMatchScore(books); // Highest match score first

  // Group by author
  const byAuthor = groupByAuthor(books);
  // → { "J.K. Rowling": [...], "Brandon Sanderson": [...] }

  // Group by genre
  const byGenre = groupByGenre(books);
  // → { "Fantasy": [...], "Science Fiction": [...] }

  return <div>See console for results</div>;
}

// ============================================================================
// PRZYKŁAD 10: Używanie styles/theme
// ============================================================================

import { COLORS, pageStyles, animations } from './styles/theme';
import { Box, Typography, Card } from '@mui/material';

function ThemeExample() {
  return (
    <>
      {/* Używanie kolorów */}
      <Box sx={{ bgcolor: COLORS.bgDark, color: COLORS.textPrimary }}>
        <Typography sx={{ color: COLORS.accent }}>Highlighted text</Typography>
      </Box>

      {/* Używanie predefiniowanych stylów */}
      <Typography sx={pageStyles.sectionTitle}>Section Title</Typography>

      {/* Używanie animacji */}
      <Card sx={{ ...animations.cardHover }}>Hover me!</Card>

      {/* Łączenie stylów */}
      <Box
        sx={{
          ...pageStyles.sectionContainer,
          bgcolor: COLORS.bgMedium,
          ...animations.fadeIn,
        }}
      >
        Combined styles
      </Box>
    </>
  );
}

// ============================================================================
// PRZYKŁAD 11: Pełna strona rekomendacji (uproszczona)
// ============================================================================

import { Container } from '@mui/material';

function SimplifiedRecommendationsPage() {
  const { loading, error, data, refetch } = useRecommendationsData({
    enabled: true,
    lambda: 0.7,
    authorLimit: true,
  });

  return (
    <Box sx={pageStyles.mainContainer}>
      <Container maxWidth="lg">
        {/* Header */}
        <Typography variant="h4" sx={{ color: 'white', mb: 4 }}>
          Twoje rekomendacje
        </Typography>

        {/* MMR Controls */}
        {/* ... */}

        {/* All Sections */}
        <TopRecommendations books={data.topRecommendations} loading={loading} mmrEnabled={true} />

        <BecauseYouBorrowed sections={data.becauseSections} loading={loading} />

        <GenreRecommendations genreSections={data.genreSections} loading={loading} />

        {/* ... other sections */}
      </Container>
    </Box>
  );
}

// ============================================================================
// EKSPORT PRZYKŁADÓW
// ============================================================================

export {
  BookCardExample,
  HorizontalScrollExample,
  SectionTitleExample,
  LoadingExample,
  CompleteSection,
  MMRExample,
  SectionsExample,
  useRecommendationsData,
  MyRecommendationsPage,
  BookHelpersExample,
  ThemeExample,
  SimplifiedRecommendationsPage,
};

// ============================================================================
// QUICK START
// ============================================================================

/*

## Quick Start - Jak zacząć?

### 1. Skopiuj pliki do projektu
```bash
cp -r recommendations-refactor/* src/pages/recommendations/
```

### 2. Użyj głównego komponentu
```jsx
import RecommendationsPage from './pages/recommendations/RecommendationsPage';

// W routing:
<Route path="/recommendations" element={<RecommendationsPage />} />
```

### 3. Lub zbuduj własną stronę z komponentów:
```jsx
import {
  TopRecommendations,
  BecauseYouBorrowed,
  MMRControlPanel
} from './pages/recommendations';

function MyCustomPage() {
  // Your implementation
}
```

### 4. Używaj pomocniczych funkcji:
```jsx
import { getBookImage, sortByMatchScore } from './pages/recommendations';

const image = getBookImage(book);
const sorted = sortByMatchScore(books);
```

### 5. Stylizuj używając theme:
```jsx
import { COLORS, pageStyles } from './pages/recommendations';

<Box sx={{ bgcolor: COLORS.bgDark }}>
  <Typography sx={pageStyles.sectionTitle}>Title</Typography>
</Box>
```

## That's it! 🚀

Wszystkie komponenty są w pełni udokumentowane i gotowe do użycia.
Zobacz README.md i MIGRATION_GUIDE.md dla więcej szczegółów.

*/
