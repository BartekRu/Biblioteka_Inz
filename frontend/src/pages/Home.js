import React from 'react';
import {
  Container,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  Button,
  Paper
} from '@mui/material';
import {
  MenuBook,
  Recommend,
  LocalLibrary,
  TrendingUp
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Home = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();

  const features = [
    {
      icon: <MenuBook sx={{ fontSize: 60 }} />,
      title: 'Bogaty Katalog',
      description: 'Tysiące książek z różnych gatunków i dla każdego wieku'
    },
    {
      icon: <Recommend sx={{ fontSize: 60 }} />,
      title: 'Rekomendacje AI',
      description: 'Inteligentny system rekomendacji dopasowany do Twoich preferencji'
    },
    {
      icon: <LocalLibrary sx={{ fontSize: 60 }} />,
      title: 'Łatwe Wypożyczanie',
      description: 'Rezerwuj i wypożyczaj książki online w prosty sposób'
    },
    {
      icon: <TrendingUp sx={{ fontSize: 60 }} />,
      title: 'Śledź Postępy',
      description: 'Monitoruj swoją historię czytania i odkrywaj nowe książki'
    }
  ];

  return (
    <Box>
      {/* Hero Section */}
      <Paper
        sx={{
          background: 'linear-gradient(45deg, #1976d2 30%, #42a5f5 90%)',
          color: 'white',
          py: 8,
          mb: 6
        }}
      >
        <Container maxWidth="lg">
          <Typography variant="h2" component="h1" gutterBottom align="center">
            Witaj w Bibliotece Miejskiej
          </Typography>
          <Typography variant="h5" align="center" paragraph>
            Odkryj świat książek z inteligentnym systemem rekomendacji
          </Typography>
          {isAuthenticated ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
              <Button
                variant="contained"
                size="large"
                color="secondary"
                onClick={() => navigate('/books')}
                sx={{ mr: 2 }}
              >
                Przeglądaj Katalog
              </Button>
              <Button
                variant="outlined"
                size="large"
                sx={{ color: 'white', borderColor: 'white' }}
                onClick={() => navigate('/recommendations')}
              >
                Moje Rekomendacje
              </Button>
            </Box>
          ) : (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
              <Button
                variant="contained"
                size="large"
                color="secondary"
                onClick={() => navigate('/register')}
                sx={{ mr: 2 }}
              >
                Zarejestruj się
              </Button>
              <Button
                variant="outlined"
                size="large"
                sx={{ color: 'white', borderColor: 'white' }}
                onClick={() => navigate('/login')}
              >
                Zaloguj się
              </Button>
            </Box>
          )}
        </Container>
      </Paper>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ mb: 8 }}>
        <Typography variant="h4" component="h2" gutterBottom align="center" sx={{ mb: 4 }}>
          Dlaczego nasza biblioteka?
        </Typography>
        <Grid container spacing={4}>
          {features.map((feature, index) => (
            <Grid item xs={12} sm={6} md={3} key={index}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  textAlign: 'center',
                  p: 2,
                  transition: 'transform 0.3s',
                  '&:hover': {
                    transform: 'translateY(-8px)',
                    boxShadow: 6
                  }
                }}
              >
                <Box sx={{ color: 'primary.main', mb: 2 }}>
                  {feature.icon}
                </Box>
                <CardContent>
                  <Typography variant="h6" component="h3" gutterBottom>
                    {feature.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {feature.description}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* CTA Section */}
      {!isAuthenticated && (
        <Paper
          sx={{
            bgcolor: 'grey.100',
            py: 6
          }}
        >
          <Container maxWidth="md">
            <Typography variant="h4" component="h2" gutterBottom align="center">
              Dołącz do naszej społeczności czytelników
            </Typography>
            <Typography variant="body1" align="center" paragraph>
              Załóż darmowe konto i zacznij odkrywać tysiące książek dostosowanych do Twoich zainteresowań
            </Typography>
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
              <Button
                variant="contained"
                size="large"
                onClick={() => navigate('/register')}
              >
                Zarejestruj się teraz
              </Button>
            </Box>
          </Container>
        </Paper>
      )}
    </Box>
  );
};

export default Home;
