import React, { useEffect, useState } from 'react';
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
} from '@mui/material';
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
const [recLoading, setRecLoading] = useState(true);
const [recError, setRecError] = useState('');


useEffect(() => {
  const fetchProfileAndRecs = async () => {
    try {
      const res = await usersAPI.getMe();
      setProfile(res.data);

      // Po pobraniu profilu spróbuj pobrać rekomendacje
      try {
        const recRes = await usersAPI.getRecommendations({ n: 8 });
        setRecommendations(recRes.data);
      } catch (err) {
        console.error(err);
        const status = err.response?.status;

        if (status === 400) {
          setRecError(
            'Brak przypisanego goodbooks_user_id – uzupełnij je w profilu, aby zobaczyć rekomendacje.'
          );
        } else {
          setRecError('Nie udało się pobrać rekomendacji.');
        }
      }
    } catch (err) {
      console.error(err);
      setError('Nie udało się pobrać profilu użytkownika.');
    } finally {
      setRecLoading(false);
    }
  };

  fetchProfileAndRecs();
}, []);


  const handleFieldChange = (field) => (e) => {
    setProfile((prev) => ({
      ...prev,
      [field]: e.target.value,
    }));
  };

  const handleAddChip = (field, value, setInput) => {
    if (!value.trim()) return;
    setProfile((prev) => ({
      ...prev,
      [field]: [...(prev[field] || []), value.trim()],
    }));
    setInput('');
  };

  const handleDeleteChip = (field, chipToDelete) => {
    setProfile((prev) => ({
      ...prev,
      [field]: (prev[field] || []).filter((item) => item !== chipToDelete),
    }));
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
    } catch (err) {
      console.error(err);
      setError('Nie udało się zapisać zmian.');
    } finally {
      setSaving(false);
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
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          Mój profil
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {success}
          </Alert>
        )}

        <Box sx={{ display: 'grid', gap: 2, mb: 3 }}>
          <TextField
            label="Nazwa użytkownika"
            value={profile.username}
            disabled
          />
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
          <TextField label="Rola" value={profile.role} disabled />
          <TextField
            label="123"
            type="number"
            value={profile.goodbooks_user_id ?? ''}
            onChange={(e) =>
              setProfile((prev) => ({
                ...prev,
                goodbooks_user_id:
                  e.target.value === '' ? null : Number(e.target.value),
              }))
            }
          />
        </Box>

        {/* Ulubione gatunki */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            Ulubione gatunki
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 1 }}>
            {(profile.favorite_genres || []).map((genre) => (
              <Chip
                key={genre}
                label={genre}
                onDelete={() => handleDeleteChip('favorite_genres', genre)}
                sx={{ mb: 1 }}
              />
            ))}
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
              value={genreInput}
              onChange={(e) => setGenreInput(e.target.value)}
            />
            <Button type="submit" variant="contained" disabled={!genreInput.trim()}>
              Dodaj
            </Button>
          </Box>
        </Box>

        {/* Ulubieni autorzy */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            Ulubieni autorzy
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 1 }}>
            {(profile.favorite_authors || []).map((author) => (
              <Chip
                key={author}
                label={author}
                onDelete={() =>
                  handleDeleteChip('favorite_authors', author)
                }
                sx={{ mb: 1 }}
              />
            ))}
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
              value={authorInput}
              onChange={(e) => setAuthorInput(e.target.value)}
            />
            <Button type="submit" variant="contained" disabled={!authorInput.trim()}>
              Dodaj
            </Button>
          </Box>
        </Box>

        {/* Historia czytania – na razie jako lista ID */}
                {/* ... HISTORIA CZYTANIA ... */}

        {/* Rekomendacje */}
        <Box sx={{ mt: 4 }}>
          <Typography variant="h6" gutterBottom>
            Polecane dla Ciebie
          </Typography>

          {recLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
              <CircularProgress size={24} />
            </Box>
          ) : recError ? (
            <Alert severity="info" sx={{ mt: 1 }}>
              {recError}
            </Alert>
          ) : recommendations.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              Na razie brak rekomendacji.
            </Typography>
          ) : (
            <Stack direction="row" spacing={2} flexWrap="wrap" sx={{ mt: 1 }}>
              {recommendations.map((rec) => (
                <Paper
                  key={rec.book_id}
                  sx={{ p: 2, width: 260, mb: 2 }}
                  elevation={2}
                >
                  <Typography variant="subtitle1" fontWeight={600}>
                    {rec.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {rec.author}
                  </Typography>

                  {rec.average_rating != null && (
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      Średnia ocena:{' '}
                      {Number(rec.average_rating).toFixed(2)}
                    </Typography>
                  )}

                  <Typography variant="caption" color="text.secondary">
                    Score modelu: {Number(rec.score).toFixed(3)}
                  </Typography>
                </Paper>
              ))}
            </Stack>
          )}
        </Box>

        <Box sx={{ textAlign: 'right', mt: 3 }}>
          <Button variant="contained" onClick={handleSave} disabled={saving}>
            {saving ? 'Zapisywanie...' : 'Zapisz zmiany'}
          </Button>
        </Box>

      </Paper>
    </Container>
  );
};

export default UserProfile;
