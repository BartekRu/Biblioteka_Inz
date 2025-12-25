/**
 * MMRControlPanel.jsx - Panel sterowania rekomendacjami (MMR settings)
 */

import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Chip,
  Switch,
  FormControlLabel,
  Collapse,
  Slider,
  Tooltip,
  Alert,
} from '@mui/material';
import {
  TuneOutlined,
  InfoOutlined,
  ExpandMore as ExpandMoreIcon,
  Category,
  LocalLibrary,
  AutoAwesome,
} from '@mui/icons-material';
import { COLORS } from '../../styles/theme';
import LoadingSkeleton from '../shared/LoadingSkeleton';

const MMRControlPanel = ({
  mmrEnabled,
  onMmrToggle,
  lambdaValue,
  onLambdaChange,
  authorLimit,
  onAuthorLimitToggle,
  maxPerAuthor,
  diversityMetrics,
  loading,
}) => {
  const [expanded, setExpanded] = useState(false);

  if (loading) {
    return (
      <Box sx={{ mb: 3 }}>
        <LoadingSkeleton.Section showTitle={false} cardCount={1} />
      </Box>
    );
  }

  return (
    <Paper
      sx={{
        p: 2,
        mb: 3,
        background: 'linear-gradient(135deg, #1e3a50 0%, #2a475e 100%)',
        border: `1px solid ${COLORS.bgMedium}`,
        borderRadius: 2,
      }}
    >
      {/* Header - zawsze widoczny */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TuneOutlined sx={{ color: COLORS.accent }} />
          <Typography variant="subtitle1" sx={{ color: COLORS.textPrimary, fontWeight: 500 }}>
            Ustawienia rekomendacji {mmrEnabled && '(MMR aktywny)'}
          </Typography>
          <Tooltip title="MMR - balansuje trafność i różnorodność rekomendacji">
            <IconButton size="small">
              <InfoOutlined sx={{ fontSize: 16, color: COLORS.textSecondary }} />
            </IconButton>
          </Tooltip>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {/* Quick toggle */}
          <FormControlLabel
            control={
              <Switch
                checked={mmrEnabled}
                onChange={(e) => {
                  e.stopPropagation();
                  onMmrToggle(e.target.checked);
                }}
                sx={{
                  '& .MuiSwitch-switchBase.Mui-checked': {
                    color: COLORS.accent,
                  },
                }}
              />
            }
            label={
              <Typography variant="caption" sx={{ color: COLORS.textSecondary }}>
                {mmrEnabled ? 'Włączone' : 'Wyłączone'}
              </Typography>
            }
            onClick={(e) => e.stopPropagation()}
          />

          <IconButton
            sx={{
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.3s',
              color: COLORS.textSecondary,
            }}
          >
            <ExpandMoreIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Expandable Content */}
      <Collapse in={expanded}>
        <Box sx={{ mt: 3 }}>
          {/* Lambda Slider - tylko gdy MMR włączony */}
          {mmrEnabled && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="body2" sx={{ color: COLORS.textPrimary, mb: 1 }}>
                Balans trafność / różnorodność (λ = {lambdaValue.toFixed(2)})
              </Typography>

              <Slider
                value={lambdaValue}
                onChange={(e, newValue) => onLambdaChange(newValue)}
                min={0}
                max={1}
                step={0.1}
                marks={[
                  { value: 0, label: '🎲 Odkrywaj' },
                  { value: 0.5, label: '⚖️ Balans' },
                  { value: 1, label: '🎯 Trafność' },
                ]}
                sx={{
                  color: COLORS.accent,
                  '& .MuiSlider-markLabel': {
                    color: COLORS.textSecondary,
                    fontSize: '0.7rem',
                  },
                  '& .MuiSlider-thumb': {
                    width: 20,
                    height: 20,
                  },
                }}
              />

              <Typography
                variant="caption"
                sx={{ color: COLORS.textSecondary, display: 'block', mt: 1, fontStyle: 'italic' }}
              >
                {lambdaValue >= 0.8 &&
                  '→ Wysoka trafność: książki najbardziej pasujące do Twoich gustów'}
                {lambdaValue >= 0.5 &&
                  lambdaValue < 0.8 &&
                  '→ Balans: mieszanka trafnych i odkrywczych rekomendacji'}
                {lambdaValue < 0.5 && '→ Wysoka różnorodność: odkryjesz nowe gatunki i autorów'}
              </Typography>
            </Box>
          )}

          {/* Author Limit - tylko gdy MMR włączony */}
          {mmrEnabled && (
            <Box sx={{ mb: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={authorLimit}
                    onChange={(e) => onAuthorLimitToggle(e.target.checked)}
                    sx={{
                      '& .MuiSwitch-switchBase.Mui-checked': {
                        color: COLORS.successGreen,
                      },
                    }}
                  />
                }
                label={
                  <Typography variant="body2" sx={{ color: COLORS.textPrimary }}>
                    Ogranicz książki tego samego autora (max {maxPerAuthor})
                  </Typography>
                }
              />
              <Typography
                variant="caption"
                sx={{ color: COLORS.textSecondary, display: 'block', ml: 5 }}
              >
                Zapobiega dominacji jednego autora (np. 10x Nora Roberts)
              </Typography>
            </Box>
          )}

          {/* Diversity Metrics - tylko gdy MMR włączony */}
          {mmrEnabled && diversityMetrics && (
            <Box
              sx={{
                mt: 3,
                p: 2,
                bgcolor: 'rgba(0,0,0,0.3)',
                borderRadius: 1,
                border: `1px solid ${COLORS.bgDark}`,
              }}
            >
              <Typography
                variant="caption"
                sx={{ color: COLORS.textSecondary, display: 'block', mb: 1 }}
              >
                📊 Metryki różnorodności aktualnych rekomendacji:
              </Typography>

              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Chip
                  label={`${diversityMetrics.unique_genres || 0} gatunków`}
                  size="small"
                  icon={<Category sx={{ fontSize: 14 }} />}
                  sx={{ bgcolor: COLORS.bgDark, color: COLORS.accent }}
                />
                <Chip
                  label={`${diversityMetrics.unique_authors || 0} autorów`}
                  size="small"
                  icon={<LocalLibrary sx={{ fontSize: 14 }} />}
                  sx={{ bgcolor: COLORS.bgDark, color: COLORS.successGreen }}
                />
                <Chip
                  label={`Różnorodność: ${(
                    (diversityMetrics.avg_pairwise_dissimilarity || 0) * 100
                  ).toFixed(0)}%`}
                  size="small"
                  icon={<AutoAwesome sx={{ fontSize: 14 }} />}
                  sx={{ bgcolor: COLORS.bgDark, color: COLORS.goldAccent }}
                />
              </Box>

              <Typography
                variant="caption"
                sx={{ color: COLORS.textSecondary, display: 'block', mt: 1 }}
              >
                💡 Im wyższe wartości, tym bardziej zróżnicowane rekomendacje
              </Typography>
            </Box>
          )}

          {/* Info gdy MMR wyłączony */}
          {!mmrEnabled && (
            <Alert severity="info" sx={{ mt: 2 }}>
              MMR wyłączony - rekomendacje bazują tylko na trafności (może wystąpić powtarzalność)
            </Alert>
          )}
        </Box>
      </Collapse>
    </Paper>
  );
};

export default MMRControlPanel;
