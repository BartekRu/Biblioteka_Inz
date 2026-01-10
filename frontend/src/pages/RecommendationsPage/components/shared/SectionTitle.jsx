import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import { COLORS, pageStyles } from '../../styles/theme';

const SectionTitle = ({ icon: Icon, title, actionLabel, onAction, subtitle }) => {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        mb: 2,
      }}
    >
      <Box>
        <Typography sx={pageStyles.sectionTitle}>
          {Icon && <Icon sx={{ color: COLORS.accent }} />}
          {title}
        </Typography>
        {subtitle && (
          <Typography variant="caption" sx={{ color: COLORS.textSecondary, ml: 4 }}>
            {subtitle}
          </Typography>
        )}
      </Box>

      {actionLabel && onAction && (
        <Button
          size="small"
          sx={{
            color: COLORS.accent,
            textTransform: 'none',
            '&:hover': {
              bgcolor: 'rgba(102, 192, 244, 0.1)',
            },
          }}
          onClick={onAction}
        >
          {actionLabel}
        </Button>
      )}
    </Box>
  );
};

export default SectionTitle;
