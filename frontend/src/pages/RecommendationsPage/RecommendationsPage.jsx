import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Box, Container, Typography, Alert, Divider } from '@mui/material';
import { Psychology } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useRecommendations } from '../../context/RecommendationsContext';
import { recommendationsAPI } from '../../services/api';

import { COLORS, pageStyles } from './styles/theme';

import TopRecommendations from './components/sectionA/TopRecommendations';

import BecauseYouBorrowed from './components/sectionB/BecauseYouBorrowed';
import GenreRecommendations from './components/sectionB/GenreRecommendations';
import AuthorBooks from './components/sectionB/AuthorBooks';
import SimilarReaders from './components/sectionB/SimilarReaders';

import DiverseDiscovery from './components/sectionC/DiverseDiscovery';
import NewArrivals from './components/sectionC/NewArrivals';
import HiddenGems from './components/sectionC/HiddenGems';
import HighlyRated from './components/sectionC/HighlyRated';

const RecommendationsPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { refreshTrigger } = useRecommendations();
  const prevTriggerRef = useRef(refreshTrigger);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const mmrEnabled = true;
  const lambdaValue = 0.7;
  const authorLimit = true;
  const maxPerAuthor = 2;

  const [topRecommendations, setTopRecommendations] = useState([]);
  const [diversityMetrics, setDiversityMetrics] = useState(null);
  const [becauseSections, setBecauseSections] = useState([]);
  const [genreSections, setGenreSections] = useState([]);
  const [authorSections, setAuthorSections] = useState([]);
  const [similarReadersBooks, setSimilarReadersBooks] = useState([]);
  const [similarUserCount, setSimilarUserCount] = useState(0);
  const [diverseBooks, setDiverseBooks] = useState([]);
  const [newArrivals, setNewArrivals] = useState([]);

  const [hiddenGems, setHiddenGems] = useState([]);
  const [highlyRated, setHighlyRated] = useState([]);

  const [modelMetrics, setModelMetrics] = useState(null);

  const fetchAllRecommendations = useCallback(async () => {
    if (!user) {
      navigate('/login');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const [
        topRecsRes,
        becauseRes,
        genreRes,
        authorRes,
        similarReadersRes,
        diverseRes,
        newArrivalsRes,
        hiddenGemsRes,
        highlyRatedRes,
        metricsRes,
      ] = await Promise.allSettled([
        recommendationsAPI.getUserLightGCN(
          30,
          0,
          mmrEnabled,
          lambdaValue,
          authorLimit,
          maxPerAuthor
        ),

        recommendationsAPI.getBecauseYouBorrowed(3, 12),

        recommendationsAPI.getGenreRecommendations(2, 20),

        recommendationsAPI.getAuthorRecommendations(1, 20),

        recommendationsAPI.getSimilarReadersBooks(30),

        recommendationsAPI.getUserLightGCN(16, 0, true, 0.3, true, maxPerAuthor),

        recommendationsAPI.getNewArrivals(40),

        recommendationsAPI.getHiddenGems(30),

        recommendationsAPI.getHighlyRated(30),

        recommendationsAPI.getModelMetrics(),
      ]);

      if (topRecsRes.status === 'fulfilled') {
        const data = topRecsRes.value.data;
        const recs = data.recommendations || (Array.isArray(data) ? data : []);
        const metadata = data.metadata || {};

        setTopRecommendations(recs);
        if (metadata.diversity_metrics) {
          setDiversityMetrics(metadata.diversity_metrics);
        }
      }

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

      if (diverseRes.status === 'fulfilled') {
        const data = diverseRes.value.data;
        const recs = data.recommendations || (Array.isArray(data) ? data : []);
        setDiverseBooks(recs);
      }

      if (newArrivalsRes.status === 'fulfilled') {
        const books = newArrivalsRes.value.data || [];
        setNewArrivals(books);
      }

      if (hiddenGemsRes.status === 'fulfilled') {
        const books = hiddenGemsRes.value.data || [];
        setHiddenGems(books);
      } else {
        console.warn('⚠️ Hidden Gems endpoint failed:', hiddenGemsRes.reason);
      }

      if (highlyRatedRes.status === 'fulfilled') {
        const books = highlyRatedRes.value.data || [];
        setHighlyRated(books);
      } else {
        console.warn('⚠️ Highly Rated endpoint failed:', highlyRatedRes.reason);
      }

      if (metricsRes.status === 'fulfilled') {
        setModelMetrics(metricsRes.value.data);
      }
    } catch (err) {
      console.error('❌ Error fetching recommendations:', err);
      setError('Nie udało się załadować rekomendacji. Spróbuj ponownie.');
    } finally {
      setLoading(false);
    }
  }, [user, navigate, mmrEnabled, lambdaValue, authorLimit, maxPerAuthor]);

  useEffect(() => {
    if (prevTriggerRef.current !== refreshTrigger) {
      prevTriggerRef.current = refreshTrigger;
      if (user) {
        fetchAllRecommendations();
      }
    }
  }, [refreshTrigger, user, fetchAllRecommendations]);

  useEffect(() => {
    if (user) {
      fetchAllRecommendations();
    }
  }, [user, fetchAllRecommendations]);

  if (!user) {
    return null;
  }

  return (
    <Box sx={pageStyles.mainContainer}>
      <Container maxWidth="xl" sx={{ width: '96vw' }}>
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

        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <TopRecommendations books={topRecommendations} loading={loading} mmrEnabled={mmrEnabled} />

        <Divider sx={{ my: 6, borderColor: COLORS.bgMedium }} />

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

        <HiddenGems books={hiddenGems} loading={loading} />

        <HighlyRated books={highlyRated} minRating={4.5} loading={loading} />

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
