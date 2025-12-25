import React, { useEffect, useState, useCallback } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Chip,
  Button,
  CircularProgress,
  Alert,
  Divider,
  Card,
  CardContent,
  Rating,
  Grid,
  Stack,
} from '@mui/material';

import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import RefreshIcon from '@mui/icons-material/Refresh';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import StarIcon from '@mui/icons-material/Star';
import PersonIcon from '@mui/icons-material/Person';
import { recommendationsAPI } from '../services/api';

import { usersAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const UserProfile = () => {
  const { loading: authLoading } = useAuth();

  const [profile, setProfile] = useState(null);

  const [recommendations, setRecommendations] = useState([]);
  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState('');
  const [recOffset, setRecOffset] = useState(0);

  const [stats, setStats] = useState(null);
  // statsLoading removed - not used in UI

  /* ============================
     FETCH STATS (INTERACTIONS)
  ============================ */
  const fetchStats = useCallback(async () => {
    // setStatsLoading(true); // Removed
    try {
      const res = await usersAPI.getUserStats();
      setStats(res.data);
    } catch (err) {
      console.error('Stats error:', err);
    }
    // finally block removed - statsLoading not used
  }, []);

  /* ============================
     FETCH RECOMMENDATIONS
  ============================ */
  const fetchRecommendations = useCallback(async (offset = 0) => {
    setRecLoading(true);
    setRecError('');
    try {
      // ✅ Używamy recommendationsAPI.getUserLightGCN zamiast usersAPI
      const res = await recommendationsAPI.getUserLightGCN(
        8, // limit
        offset, // offset dla rotacji
        true, // use_mmr
        0.7, // lambda_param
        true, // enforce_author_limit
        2 // max_per_author
      );

      // ✅ Obsługa nowego formatu z metadata
      const data = res.data;
      const recs = data.recommendations || data || [];

      setRecommendations(Array.isArray(recs) ? recs : []);
      setRecOffset(offset);
    } catch (err) {
      const status = err.response?.status;
      setRecError(
        status === 400
          ? 'Brak wystarczających interakcji do wygenerowania rekomendacji.'
          : 'Nie udało się pobrać rekomendacji.'
      );
    } finally {
      setRecLoading(false);
    }
  }, []);

  /* ============================
     INIT
  ============================ */
  useEffect(() => {
    const fetchProfile = async () => {
      const res = await usersAPI.getMe();
      setProfile(res.data);
    };

    fetchProfile();
    fetchStats();
    fetchRecommendations(0);
  }, [fetchStats, fetchRecommendations]);

  /* ============================
     HELPERS
  ============================ */
  const handleNextRecommendations = () => {
    fetchRecommendations(recOffset + 8);
  };

  const getRecommendationTypeLabel = (type) => {
    switch (type) {
      case 'collaborative':
        return { label: 'AI', color: 'primary' };
      case 'interaction_based':
        return { label: 'Na podstawie Twoich interakcji', color: 'success' };
      case 'content_based':
        return { label: 'Dopasowane', color: 'success' };
      case 'popular':
        return { label: 'Popularne', color: 'default' };
      default:
        return { label: type, color: 'default' };
    }
  };

  /* ============================
     LOADING
  ============================ */
  if (authLoading || !profile) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  /* ============================
     RENDER
  ============================ */
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          Mój profil
        </Typography>

        {/* ============================
           STATS (INTERACTIONS)
        ============================ */}
        {stats && (
          <>
            <Box sx={{ mt: 3, p: 2, bgcolor: 'background.default', borderRadius: 2 }}>
              <Typography variant="h6" sx={{ display: 'flex', gap: 1 }}>
                <TrendingUpIcon /> Twoje statystyki (na podstawie interakcji)
              </Typography>

              <Grid container spacing={2} sx={{ mt: 2 }}>
                <Grid item xs={6} md={3}>
                  <Typography variant="h4">{stats.total_borrows}</Typography>
                  <Typography>Wypożyczeń</Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="h4">{stats.total_reviews}</Typography>
                  <Typography>Recenzji</Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="h4">{stats.total_views}</Typography>
                  <Typography>Wyświetleń</Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Typography variant="h4">{stats.avg_rating ?? 'N/A'}</Typography>
                    <StarIcon color="warning" />
                  </Box>
                  <Typography>Średnia ocen</Typography>
                </Grid>
              </Grid>

              {/* TOP 3 GENRES */}
              {stats.top_genres?.length > 0 && (
                <Box sx={{ mt: 3 }}>
                  <Typography fontWeight={600} gutterBottom>
                    📊 Twoje TOP 3 gatunki (z interakcji)
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap">
                    {stats.top_genres.map((g, idx) => (
                      <Chip
                        key={g.genre}
                        label={`${idx + 1}. ${g.genre} (${g.count})`}
                        color={idx === 0 ? 'primary' : 'default'}
                        sx={{ fontWeight: idx === 0 ? 700 : 500 }}
                      />
                    ))}
                  </Stack>
                </Box>
              )}

              {/* ✅ TOP 3 AUTHORS - NOWA SEKCJA */}
              {stats.top_authors?.length > 0 && (
                <Box sx={{ mt: 3 }}>
                  <Typography
                    fontWeight={600}
                    gutterBottom
                    sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
                  >
                    <PersonIcon color="secondary" /> Twoi TOP 3 autorzy (z interakcji)
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap">
                    {stats.top_authors.map((a, idx) => (
                      <Chip
                        key={a.author}
                        label={`${idx + 1}. ${a.author} (${a.count})`}
                        color={idx === 0 ? 'secondary' : 'default'}
                        variant={idx === 0 ? 'filled' : 'outlined'}
                        sx={{ fontWeight: idx === 0 ? 700 : 500 }}
                      />
                    ))}
                  </Stack>
                </Box>
              )}

              {/* INFO: Brak interakcji */}
              {(!stats.top_genres || stats.top_genres.length === 0) &&
                (!stats.top_authors || stats.top_authors.length === 0) && (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    Brak wystarczających interakcji. Wypożycz lub oceń książki, aby zobaczyć swoje
                    preferencje!
                  </Alert>
                )}
            </Box>

            <Divider sx={{ my: 4 }} />
          </>
        )}

        {/* ============================
           RECOMMENDATIONS
        ============================ */}
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6" sx={{ display: 'flex', gap: 1 }}>
              <AutoStoriesIcon /> Polecane dla Ciebie
            </Typography>

            <Button
              size="small"
              startIcon={<RefreshIcon />}
              onClick={handleNextRecommendations}
              disabled={recLoading}
            >
              Następne
            </Button>
          </Box>

          {recLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress size={24} />
            </Box>
          ) : recError ? (
            <Alert severity="info">{recError}</Alert>
          ) : recommendations.length === 0 ? (
            <Alert severity="info">
              Brak rekomendacji – wykonaj więcej interakcji (wypożyczenia, oceny, przeglądanie
              książek).
            </Alert>
          ) : (
            <Grid container spacing={2}>
              {recommendations.map((rec) => {
                const genres = Array.isArray(rec.genre) ? rec.genre : rec.genre ? [rec.genre] : [];

                const authors = Array.isArray(rec.authors)
                  ? rec.authors
                  : rec.author
                  ? [rec.author]
                  : [];

                const typeInfo = getRecommendationTypeLabel(rec.recommendation_type);

                return (
                  <Grid item xs={12} sm={6} md={3} key={rec._id}>
                    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                      <CardContent sx={{ flexGrow: 1 }}>
                        <Typography fontWeight={600} gutterBottom>
                          {rec.title}
                        </Typography>

                        {authors.length > 0 && (
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            {authors.join(', ')}
                          </Typography>
                        )}

                        {genres.length > 0 && (
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            display="block"
                            gutterBottom
                          >
                            {genres.join(', ')}
                          </Typography>
                        )}

                        {rec.average_rating && (
                          <Rating
                            value={rec.average_rating}
                            precision={0.1}
                            readOnly
                            size="small"
                            sx={{ mt: 1 }}
                          />
                        )}

                        {rec.match_reason && (
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ display: 'block', mt: 1, fontStyle: 'italic' }}
                          >
                            💡 {rec.match_reason}
                          </Typography>
                        )}

                        <Chip
                          label={typeInfo.label}
                          size="small"
                          color={typeInfo.color}
                          sx={{ mt: 1 }}
                        />
                      </CardContent>
                    </Card>
                  </Grid>
                );
              })}
            </Grid>
          )}
        </Box>
      </Paper>
    </Container>
  );
};

export default UserProfile;
