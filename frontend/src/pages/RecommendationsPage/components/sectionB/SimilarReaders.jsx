/**
 * SimilarReaders.jsx - SEKCJA B: "Popularne wśród Twoich czytelniczych bliźniaków"
 *
 * Bezpośrednia demonstracja user-based collaborative filtering z LightGCN
 * Pokazuje użytkownikom "Kim są ich podobni czytelnicy" (anonimowo)
 */

import React from 'react';
import { Box, Chip, Paper, Typography, Avatar, AvatarGroup, Alert } from '@mui/material';
import { PeopleAlt, Psychology, TrendingUp, Warning } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import SectionTitle from '../shared/SectionTitle';
import HorizontalBookScroll from '../shared/HorizontalBookScroll';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import { COLORS, pageStyles } from '../../styles/theme';
import { recommendationsAPI } from '../../../../services/api';

const SimilarReaders = ({ books, similarUserCount, loading }) => {
  const navigate = useNavigate();

  const handleBookClick = async (book) => {
    await recommendationsAPI.reportInteraction(book._id, 'view', {
      source: 'similar-readers',
    });
    navigate(`/books/${book._id}`);
  };

  if (loading) {
    return (
      <Box sx={pageStyles.sectionContainer}>
        <LoadingSkeleton.Section cardCount={4} />
      </Box>
    );
  }

  if (!books || books.length === 0) {
    return (
      <Alert severity="info">
        <Typography>Nie znaleziono podobnych czytelników.</Typography>
        <Typography variant="caption">💡 Im więcej książek wypożyczysz, tym lepiej!</Typography>
      </Alert>
    ); // ✅ NOWE
  }

  // Losowe kolory dla avatarów (reprezentują anonimowych użytkowników)
  const avatarColors = [
    COLORS.accent,
    COLORS.successGreen,
    COLORS.goldAccent,
    '#9c27b0',
    '#ff5722',
  ];

  return (
    <Box sx={pageStyles.sectionContainer}>
      {/* Section Title */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <AvatarGroup max={4} sx={{ ml: 1 }}>
          {avatarColors.slice(0, Math.min(similarUserCount || 3, 4)).map((color, idx) => (
            <Avatar
              key={idx}
              sx={{
                bgcolor: color,
                width: 32,
                height: 32,
                fontSize: '0.8rem',
                fontWeight: 600,
              }}
            >
              {String.fromCharCode(65 + idx)}
            </Avatar>
          ))}
        </AvatarGroup>

        <Box sx={{ flex: 1 }}>
          <SectionTitle
            icon={PeopleAlt}
            title="Popularne wśród Twoich czytelniczych bliźniaków"
            subtitle={`${similarUserCount || 'Wielu'} podobnych czytelników też to lubi`}
          />
        </Box>
      </Box>

      {/* Stats Chips */}
      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <Chip
          icon={<Psychology sx={{ fontSize: 14 }} />}
          label="User-based CF"
          size="small"
          sx={{
            bgcolor: 'rgba(156, 39, 176, 0.2)',
            color: '#ce93d8',
            border: '1px solid #ce93d8',
          }}
        />
        <Chip
          icon={<TrendingUp sx={{ fontSize: 14 }} />}
          label={`Top ${books.length} wyborów`}
          size="small"
          sx={{
            bgcolor: 'rgba(255, 193, 7, 0.2)',
            color: COLORS.goldAccent,
            border: `1px solid ${COLORS.goldAccent}`,
          }}
        />
      </Box>

      {/* Books Carousel */}
      <HorizontalBookScroll
        books={books.slice(0, 10)}
        onBookClick={handleBookClick}
        showScore={true}
        showReason={false}
        interactionSource="similar-readers"
      />

      {/* Explanation */}
      <Paper
        sx={{
          mt: 2,
          p: 2,
          background: 'rgba(156, 39, 176, 0.05)',
          border: `1px solid ${COLORS.bgMedium}`,
          borderRadius: 1,
        }}
      >
        <Typography variant="caption" sx={{ color: COLORS.textSecondary, display: 'block', mb: 1 }}>
          👥 <strong>Jak to działa?</strong> LightGCN znajduje czytelników o podobnych gustach do
          Twoich, analizując embeddingi użytkowników w przestrzeni ukrytej. Te książki są
          najpopularniejsze wśród osób, które mają podobny profil czytelniczy.
        </Typography>
        <Typography variant="caption" sx={{ color: COLORS.textSecondary, fontStyle: 'italic' }}>
          💡 To klasyczna filtracja kolaboracyjna oparta na użytkownikach (user-based collaborative
          filtering), zaimplementowana przez Graf Convolutional Network.
        </Typography>
      </Paper>
    </Box>
  );
};

export default SimilarReaders;
