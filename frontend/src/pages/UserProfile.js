import React, { useEffect, useState, useCallback } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  TextField,
  Chip,
  Stack,
  Button,
  CircularProgress,
  Alert,
  Divider,
  Card,
  CardContent,
  Rating,
} from '@mui/material';
import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import RefreshIcon from '@mui/icons-material/Refresh';
import { usersAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const UserProfile = () => {
  const { loading: authLoading } = useAuth();

  const [profile, setProfile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [genreInput, setGenreInput] = useState('');
  const [authorInput, setAuthorInput] = useState('');

  const [recommendations, setRecommendations] = useState([]);
  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState('');

  const fetchRecommendations = useCallback(async () => {
    setRecLoading(true);
    setRecError('');
    try {
      const recRes = await usersAPI.getRecommendations({ n: 8 });
      setRecommendations(recRes.data);
    } catch (err) {
      console.error(err);
      const status = err.response?.status;
      if (status === 400) {
        setRecError('Dodaj ulubione gatunki lub autorów, aby zobaczyć spersonalizowane rekomendacje.');
      } else {
        setRecError('Nie udało się pobrać rekomendacji.');
      }
    } finally {
      setRecLoading(false);
    }
  }, []);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await usersAPI.getMe();
        setProfile(res.data);
      } catch (err) {
        console.error(err);
        setError('Nie udało się pobrać profilu użytkownika.');
      }
    };

    fetchProfile();
    fetchRecommendations();
  }, [fetchRecommendations]);

  const handleFieldChange = (field) => (e) => {
    setProfile((prev) => ({
      ...prev,
      [field]: e.target.value,
    }));
  };

  const handleAddChip = async (field, value, setInput) => {
    if (!value.trim()) return;
    
    const newValue = [...(profile[field] || []), value.trim()];
    
    setProfile((prev) => ({
      ...prev,
      [field]: newValue,
    }));
    setInput('');
    
    try {
      await usersAPI.updateMe({ [field]: newValue });
      setSuccess(`Dodano: ${value.trim()}`);
      setTimeout(() => setSuccess(''), 2000);
      
      fetchRecommendations();
    } catch (err) {
      console.error(err);
      setError('Nie udało się zapisać zmian.');
    }
  };

  const handleDeleteChip = async (field, chipToDelete) => {
    const newValue = (profile[field] || []).filter((item) => item !== chipToDelete);
    
    setProfile((prev) => ({
      ...prev,
      [field]: newValue,
    }));
    
    try {
      await usersAPI.updateMe({ [field]: newValue });
      
      fetchRecommendations();
    } catch (err) {
      console.error(err);
      setError('Nie udało się zapisać zmian.');
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const payload = {
        email: profile.email,
        full_name: profile.full_name,
        favorite_genres: profile.favorite_genres,
        favorite_authors: profile.favorite_authors,
        goodbooks_user_id: profile.goodbooks_user_id || null,
      };
      const res = await usersAPI.updateMe(payload);
      setProfile(res.data);
      setSuccess('Profil został zaktualizowany.');
      
      fetchRecommendations();
    } catch (err) {
      console.error(err);
      setError('Nie udało się zapisać zmian.');
    } finally {
      setSaving(false);
    }
  };

  const getRecommendationTypeLabel = (type) => {
    switch (type) {
      case 'collaborative':
        return { label: 'AI', color: 'primary' };
      case 'content_based':
        return { label: 'Dopasowane', color: 'success' };
      case 'popular':
        return { label: 'Popularne', color: 'default' };
      default:
        return { label: type, color: 'default' };
    }
  };

  if (authLoading || !profile) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          Mój profil
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
            {success}
          </Alert>
        )}

        <Box sx={{ display: 'grid', gap: 2, mb: 3, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' } }}>
          <TextField
            label="Adres e-mail"
            value={profile.email}
            onChange={handleFieldChange('email')}
          />
          <TextField
            label="Imię i nazwisko"
            value={profile.full_name || ''}
            onChange={handleFieldChange('full_name')}
          />
          <TextField 
            label="Rola" 
            value={profile.role} 
            disabled 
          />
          <TextField
            label="Goodbooks User ID (opcjonalne)"
            type="number"
            value={profile.goodbooks_user_id ?? ''}
            onChange={(e) =>
              setProfile((prev) => ({
                ...prev,
                goodbooks_user_id: e.target.value === '' ? null : Number(e.target.value),
              }))
            }
            helperText="ID z datasetu goodbooks-10k (1-53424)"
          />
        </Box>

        <Divider sx={{ my: 3 }} />

        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom fontWeight={600}>
            📚 Ulubione gatunki
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Dodaj gatunki, które lubisz - rekomendacje będą dopasowane do Twoich preferencji
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 1, minHeight: 32 }}>
            {(profile.favorite_genres || []).map((genre) => (
              <Chip
                key={genre}
                label={genre}
                onDelete={() => handleDeleteChip('favorite_genres', genre)}
                color="primary"
                variant="outlined"
                sx={{ mb: 1 }}
              />
            ))}
            {(!profile.favorite_genres || profile.favorite_genres.length === 0) && (
              <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                Brak ulubionych gatunków
              </Typography>
            )}
          </Stack>
          <Box
            component="form"
            onSubmit={(e) => {
              e.preventDefault();
              handleAddChip('favorite_genres', genreInput, setGenreInput);
            }}
            sx={{ display: 'flex', gap: 1 }}
          >
            <TextField
              size="small"
              label="Dodaj gatunek"
              placeholder="np. Fantasy, Kryminał, Sci-Fi"
              value={genreInput}
              onChange={(e) => setGenreInput(e.target.value)}
              sx={{ minWidth: 200 }}
            />
            <Button type="submit" variant="contained" disabled={!genreInput.trim()}>
              Dodaj
            </Button>
          </Box>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom fontWeight={600}>
            ✍️ Ulubieni autorzy
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Dodaj autorów, których książki chciałbyś zobaczyć w rekomendacjach
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 1, minHeight: 32 }}>
            {(profile.favorite_authors || []).map((author) => (
              <Chip
                key={author}
                label={author}
                onDelete={() => handleDeleteChip('favorite_authors', author)}
                color="secondary"
                variant="outlined"
                sx={{ mb: 1 }}
              />
            ))}
            {(!profile.favorite_authors || profile.favorite_authors.length === 0) && (
              <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                Brak ulubionych autorów
              </Typography>
            )}
          </Stack>
          <Box
            component="form"
            onSubmit={(e) => {
              e.preventDefault();
              handleAddChip('favorite_authors', authorInput, setAuthorInput);
            }}
            sx={{ display: 'flex', gap: 1 }}
          >
            <TextField
              size="small"
              label="Dodaj autora"
              placeholder="np. Sapkowski, Rowling"
              value={authorInput}
              onChange={(e) => setAuthorInput(e.target.value)}
              sx={{ minWidth: 200 }}
            />
            <Button type="submit" variant="contained" disabled={!authorInput.trim()}>
              Dodaj
            </Button>
          </Box>
        </Box>

        <Divider sx={{ my: 3 }} />

        <Box sx={{ mt: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <AutoStoriesIcon /> Polecane dla Ciebie
            </Typography>
            <Button
              startIcon={<RefreshIcon />}
              onClick={fetchRecommendations}
              disabled={recLoading}
              size="small"
            >
              Odśwież
            </Button>
          </Box>

          {recLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
              <CircularProgress size={24} />
            </Box>
          ) : recError ? (
            <Alert severity="info" sx={{ mt: 1 }}>
              {recError}
            </Alert>
          ) : recommendations.length === 0 ? (
            <Alert severity="info">
              Dodaj ulubione gatunki lub autorów powyżej, aby zobaczyć spersonalizowane rekomendacje!
            </Alert>
          ) : (
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: {
                  xs: '1fr',
                  sm: 'repeat(2, 1fr)',
                  md: 'repeat(3, 1fr)',
                  lg: 'repeat(4, 1fr)',
                },
                gap: 2,
                mt: 1,
              }}
            >
              {recommendations.map((rec) => {
                const typeInfo = getRecommendationTypeLabel(rec.recommendation_type);
                return (
                  <Card key={rec.book_id} elevation={2} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <CardContent sx={{ flexGrow: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                        <Typography variant="subtitle1" fontWeight={600} sx={{ lineHeight: 1.3 }}>
                          {rec.title}
                        </Typography>
                        <Chip
                          label={typeInfo.label}
                          color={typeInfo.color}
                          size="small"
                          sx={{ ml: 1, flexShrink: 0 }}
                        />
                      </Box>
                      
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        {rec.author}
                      </Typography>

                      {rec.genre && rec.genre.length > 0 && (
                        <Box sx={{ mt: 1, mb: 1 }}>
                          {rec.genre.slice(0, 2).map((g) => (
                            <Chip
                              key={g}
                              label={g}
                              size="small"
                              variant="outlined"
                              sx={{ mr: 0.5, mb: 0.5, fontSize: '0.7rem' }}
                            />
                          ))}
                        </Box>
                      )}

                      {rec.average_rating != null && rec.average_rating > 0 && (
                        <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                          <Rating
                            value={rec.average_rating}
                            precision={0.1}
                            size="small"
                            readOnly
                          />
                          <Typography variant="body2" sx={{ ml: 1 }}>
                            {Number(rec.average_rating).toFixed(1)}
                          </Typography>
                        </Box>
                      )}

                      {rec.match_reason && (
                        <Typography
                          variant="caption"
                          color="success.main"
                          sx={{ display: 'block', mt: 1, fontStyle: 'italic' }}
                        >
                          {rec.match_reason}
                        </Typography>
                      )}

                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                        Score: {Number(rec.score).toFixed(2)}
                      </Typography>
                    </CardContent>
                  </Card>
                );
              })}
            </Box>
          )}
        </Box>

        <Box sx={{ textAlign: 'right', mt: 4 }}>
          <Button variant="contained" size="large" onClick={handleSave} disabled={saving}>
            {saving ? 'Zapisywanie...' : 'Zapisz zmiany'}
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default UserProfile;