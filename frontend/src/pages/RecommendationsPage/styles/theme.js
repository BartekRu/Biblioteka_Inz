/**
 * theme.js - Steam-inspired dark theme for library recommendations
 */

export const COLORS = {
  bgDark: '#1b2838',
  bgMedium: '#2a475e',
  bgLight: '#66c0f4',
  accent: '#66c0f4',
  accentDark: '#1a9fff',
  textPrimary: '#c7d5e0',
  textSecondary: '#8f98a0',
  cardBg: 'linear-gradient(135deg, #1e3a50 0%, #2a475e 100%)',
  cardHover: 'linear-gradient(135deg, #2a4a65 0%, #3a5a75 100%)',
  goldAccent: '#ffc107',
  successGreen: '#4caf50',
  errorRed: '#ff6b6b',
};

export const pageStyles = {
  mainContainer: {
    minHeight: '100vh',
    background: `linear-gradient(180deg, ${COLORS.bgDark} 0%, #0f1923 100%)`,
    py: 4,
  },
  sectionTitle: {
    color: COLORS.textPrimary,
    fontWeight: 300,
    textTransform: 'uppercase',
    letterSpacing: '2px',
    fontSize: '0.9rem',
    mb: 2,
    display: 'flex',
    alignItems: 'center',
    gap: 1,
  },
  carouselContainer: {
    position: 'relative',
    mb: 6,
  },
  navButton: {
    position: 'absolute',
    top: '50%',
    transform: 'translateY(-50%)',
    bgcolor: 'rgba(0,0,0,0.7)',
    color: 'white',
    '&:hover': {
      bgcolor: 'rgba(0,0,0,0.9)',
    },
    zIndex: 10,
  },
  sectionContainer: {
    mb: 6,
    position: 'relative',
  },
};

export const animations = {
  cardHover: {
    transition: 'transform 0.3s ease, box-shadow 0.3s ease',
    '&:hover': {
      transform: 'scale(1.05)',
      boxShadow: '0 8px 25px rgba(102, 192, 244, 0.3)',
    },
  },
  fadeIn: {
    animation: 'fadeIn 0.5s ease-in',
    '@keyframes fadeIn': {
      from: { opacity: 0, transform: 'translateY(20px)' },
      to: { opacity: 1, transform: 'translateY(0)' },
    },
  },
};
