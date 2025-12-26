import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Box, Container, Typography, Alert, Button, Divider } from '@mui/material';
import { Refresh, Psychology } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useRecommendations } from '../../context/RecommendationsContext';
import { recommendationsAPI } from '../../services/api';

// Styles & Utils
import { COLORS, pageStyles } from './styles/theme';

// Controls
import MMRControlPanel from './components/controls/MMRControlPanel';

// Section A
import TopRecommendations from './components/sectionA/TopRecommendations';

// Section B
import BecauseYouBorrowed from './components/sectionB/BecauseYouBorrowed';
import GenreRecommendations from './components/sectionB/GenreRecommendations';
import AuthorBooks from './components/sectionB/AuthorBooks';
import SimilarReaders from './components/sectionB/SimilarReaders';

// Section C
import DiverseDiscovery from './components/sectionC/DiverseDiscovery';
import NewArrivals from './components/sectionC/NewArrivals';
import HiddenGems from './components/sectionC/HiddenGems';
import HighlyRated from './components/sectionC/HighlyRated';

const RecommendationsPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { refreshTrigger } = useRecommendations();
  const prevTriggerRef = useRef(refreshTrigger);

  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================

  // Loading & Error
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // MMR Settings
  const [mmrEnabled, setMmrEnabled] = useState(true);
  const [lambdaValue, setLambdaValue] = useState(0.7);
  const [authorLimit, setAuthorLimit] = useState(true);
  const maxPerAuthor = 2;

  // Data for different sections
  const [topRecommendations, setTopRecommendations] = useState([]);
  const [diversityMetrics, setDiversityMetrics] = useState(null);
  const [becauseSections, setBecauseSections] = useState([]);
  const [genreSections, setGenreSections] = useState([]);
  const [authorSections, setAuthorSections] = useState([]);
  const [similarReadersBooks, setSimilarReadersBooks] = useState([]);
  const [similarUserCount, setSimilarUserCount] = useState(0);
  const [diverseBooks, setDiverseBooks] = useState([]);
  const [newArrivals, setNewArrivals] = useState([]);

  // 🆕 NOWE STATE dla Hidden Gems i Highly Rated
  const [hiddenGems, setHiddenGems] = useState([]);
  const [highlyRated, setHighlyRated] = useState([]);

  // Model metadata
  const [modelMetrics, setModelMetrics] = useState(null);

  // ============================================================================
  // EFFECTS
  // ============================================================================

  // Reaguj na zmiany refreshTrigger z kontekstu
  useEffect(() => {
    if (prevTriggerRef.current !== refreshTrigger) {
      prevTriggerRef.current = refreshTrigger;
      if (user) {
        fetchAllRecommendations();
      }
    }
  }, [refreshTrigger, user]);

  // Fetch recommendations przy zmianie MMR settings
  useEffect(() => {
    if (user) {
      fetchAllRecommendations();
    }
  }, [user, mmrEnabled, lambdaValue, authorLimit]);

  // ============================================================================
  // DATA FETCHING
  // ============================================================================

  const fetchAllRecommendations = useCallback(async () => {
    if (!user) {
      navigate('/login');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      

      // 🔧 POPRAWIONE - Parallel fetch wszystkich sekcji
      const [
        topRecsRes,
        becauseRes,
        genreRes,
        authorRes,
        similarReadersRes,
        diverseRes,
        newArrivalsRes,
        hiddenGemsRes, // 🆕 DODANE
        highlyRatedRes, // 🆕 DODANE
        metricsRes,
      ] = await Promise.allSettled([
        // SEKCJA A: Top recommendations
        recommendationsAPI.getUserLightGCN(
          30,
          0,
          mmrEnabled,
          lambdaValue,
          authorLimit,
          maxPerAuthor
        ),

        // SEKCJA B: Because you borrowed
        recommendationsAPI.getBecauseYouBorrowed(),

        // SEKCJA B: Genre recommendations
        recommendationsAPI.getGenreRecommendations(),

        // SEKCJA B: Author recommendations
        recommendationsAPI.getAuthorRecommendations(),

        // SEKCJA B: Similar readers
        recommendationsAPI.getSimilarReadersBooks(),

        // SEKCJA C: Diverse discovery (MMR z niskim λ)
        recommendationsAPI.getUserLightGCN(10, 0, true, 0.3, true, maxPerAuthor),

        // SEKCJA C: New arrivals
        recommendationsAPI.getNewArrivals(),

        // 🆕 SEKCJA C: Hidden Gems
        recommendationsAPI.getHiddenGems(),

        // 🆕 SEKCJA C: Highly Rated
        recommendationsAPI.getHighlyRated(),

        // Model metrics
        recommendationsAPI.getModelMetrics(),
      ]);

      // Process SEKCJA A
      if (topRecsRes.status === 'fulfilled') {
        const data = topRecsRes.value.data;
        const recs = data.recommendations || (Array.isArray(data) ? data : []);
        const metadata = data.metadata || {};

        setTopRecommendations(recs);
        if (metadata.diversity_metrics) {
          setDiversityMetrics(metadata.diversity_metrics);
        }

      }

      // Process SEKCJA B
      if (becauseRes.status === 'fulfilled') {
        const sections = becauseRes.value.data || [];
        setBecauseSections(sections);
      }

      if (genreRes.status === 'fulfilled') {
        const sections = genreRes.value.data || [];
        setGenreSections(sections);
      }

      if (authorRes.status === 'fulfilled') {
        const sections = authorRes.value.data || [];
        setAuthorSections(sections);
      }

      if (similarReadersRes.status === 'fulfilled') {
        const data = similarReadersRes.value.data || {};
        setSimilarReadersBooks(data.books || []);
        setSimilarUserCount(data.similar_user_count || 0);
      }

      // Process SEKCJA C
      if (diverseRes.status === 'fulfilled') {
        const data = diverseRes.value.data;
        const recs = data.recommendations || (Array.isArray(data) ? data : []);
        setDiverseBooks(recs);
      }

      if (newArrivalsRes.status === 'fulfilled') {
        const books = newArrivalsRes.value.data || [];
        setNewArrivals(books);
      }

      // 🆕 Process Hidden Gems
      if (hiddenGemsRes.status === 'fulfilled') {
        const books = hiddenGemsRes.value.data || [];
        setHiddenGems(books);
      } else {
        console.warn('⚠️ Hidden Gems endpoint failed:', hiddenGemsRes.reason);
      }

      // 🆕 Process Highly Rated
      if (highlyRatedRes.status === 'fulfilled') {
        const books = highlyRatedRes.value.data || [];
        setHighlyRated(books);
      } else {
        console.warn('⚠️ Highly Rated endpoint failed:', highlyRatedRes.reason);
      }

      // Process model metrics
      if (metricsRes.status === 'fulfilled') {
        setModelMetrics(metricsRes.value.data);
      }
    } catch (err) {
      console.error('❌ Error fetching recommendations:', err);
      setError('Nie udało się załadować rekomendacji. Spróbuj ponownie.');
    } finally {
      setLoading(false);
    }
  }, [user, navigate, mmrEnabled, lambdaValue, authorLimit]);

  // ============================================================================
  // RENDER
  // ============================================================================

  if (!user) {
    return null;
  }

  return (
    <Box sx={pageStyles.mainContainer}>
      <Container maxWidth="lg">
        {/* ====================================================================
            HEADER
        ==================================================================== */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mb: 4,
          }}
        >
          <Box>
            <Typography
              variant="h4"
              sx={{
                color: 'white',
                fontWeight: 300,
                fontFamily: '"Playfair Display", serif',
              }}
            >
              Twoje rekomendacje
            </Typography>
            <Typography variant="body2" sx={{ color: COLORS.textSecondary }}>
              Spersonalizowane dla Ciebie przez AI {mmrEnabled && '+ MMR'}
            </Typography>
          </Box>

          <Button
            startIcon={<Refresh />}
            onClick={fetchAllRecommendations}
            sx={{
              color: COLORS.accent,
              borderColor: COLORS.accent,
              '&:hover': {
                borderColor: COLORS.accentDark,
                bgcolor: 'rgba(102, 192, 244, 0.1)',
              },
            }}
            variant="outlined"
          >
            Odśwież
          </Button>
        </Box>

        {/* Error Alert */}
        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* ====================================================================
            MMR CONTROL PANEL
        ==================================================================== */}
        <MMRControlPanel
          mmrEnabled={mmrEnabled}
          onMmrToggle={setMmrEnabled}
          lambdaValue={lambdaValue}
          onLambdaChange={setLambdaValue}
          authorLimit={authorLimit}
          onAuthorLimitToggle={setAuthorLimit}
          maxPerAuthor={maxPerAuthor}
          diversityMetrics={diversityMetrics}
          loading={loading}
        />

        {/* ====================================================================
            SEKCJA A: GŁÓWNE REKOMENDACJE
        ==================================================================== */}
        <TopRecommendations books={topRecommendations} loading={loading} mmrEnabled={mmrEnabled} />

        <Divider sx={{ my: 6, borderColor: COLORS.bgMedium }} />

        {/* ====================================================================
            SEKCJA B: REKOMENDACJE WYJAŚNIALNE
        ==================================================================== */}
        <Typography
          variant="h5"
          sx={{
            color: COLORS.textPrimary,
            fontWeight: 300,
            mb: 3,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <Psychology sx={{ color: COLORS.accent }} />
          Dlaczego to polecamy?
        </Typography>

        <BecauseYouBorrowed sections={becauseSections} loading={loading} />

        <GenreRecommendations genreSections={genreSections} loading={loading} />

        <AuthorBooks authorSections={authorSections} loading={loading} />

        <SimilarReaders
          books={similarReadersBooks}
          similarUserCount={similarUserCount}
          loading={loading}
        />

        <Divider sx={{ my: 6, borderColor: COLORS.bgMedium }} />

        {/* ====================================================================
            SEKCJA C: ODKRYWANIE
        ==================================================================== */}
        <Typography
          variant="h5"
          sx={{
            color: COLORS.textPrimary,
            fontWeight: 300,
            mb: 3,
          }}
        >
          Odkryj coś nowego
        </Typography>

        <DiverseDiscovery books={diverseBooks} diversityScore={0.8} loading={loading} />

        <NewArrivals books={newArrivals} loading={loading} />

        {/* 🆕 NOWE SEKCJE */}
        <HiddenGems books={hiddenGems} loading={loading} />

        <HighlyRated books={highlyRated} minRating={4.5} loading={loading} />

        {/* ====================================================================
            FOOTER INFO
        ==================================================================== */}
        <Box
          sx={{
            textAlign: 'center',
            py: 4,
            borderTop: `1px solid ${COLORS.bgMedium}`,
            mt: 6,
          }}
        >
          <Typography variant="body2" sx={{ color: COLORS.textSecondary }}>
            Rekomendacje generowane przez model LightGCN {mmrEnabled && '+ MMR re-ranking'}{' '}
            wytrenowany na {modelMetrics?.interactions?.toLocaleString() || '932,940'} interakcjach
          </Typography>
          <Typography
            variant="caption"
            sx={{ color: COLORS.textSecondary, display: 'block', mt: 1 }}
          >
            {mmrEnabled && diversityMetrics
              ? `🎨 Różnorodność: ${diversityMetrics.unique_authors || 'N/A'} autorów, ${
                  diversityMetrics.unique_genres || 'N/A'
                } gatunków`
              : 'Im więcej wypożyczasz i oceniasz książek, tym lepsze rekomendacje otrzymasz'}
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default RecommendationsPage;
