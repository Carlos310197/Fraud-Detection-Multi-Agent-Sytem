import React from 'react';
import { Box, LinearProgress, Typography, Tooltip } from '@mui/material';

interface ConfidenceBarProps {
  confidence: number;
}

const getConfidenceColor = (confidence: number): 'success' | 'warning' | 'error' => {
  if (confidence < 0.45) return 'success';
  if (confidence < 0.75) return 'warning';
  return 'error';
};

const getConfidenceLabel = (confidence: number): string => {
  if (confidence < 0.45) return 'Bajo riesgo';
  if (confidence < 0.60) return 'Riesgo moderado';
  if (confidence < 0.75) return 'Riesgo elevado';
  return 'Alto riesgo';
};

export const ConfidenceBar: React.FC<ConfidenceBarProps> = ({ confidence }) => {
  const percentage = Math.round(confidence * 100);

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
        <Typography variant="body2" color="text.secondary">
          Confianza de fraude
        </Typography>
        <Tooltip title={getConfidenceLabel(confidence)}>
          <Typography variant="body2" fontWeight="medium">
            {percentage}%
          </Typography>
        </Tooltip>
      </Box>
      <LinearProgress
        variant="determinate"
        value={percentage}
        color={getConfidenceColor(confidence)}
        sx={{ height: 8, borderRadius: 4 }}
      />
      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
        {getConfidenceLabel(confidence)}
      </Typography>
    </Box>
  );
};

export default ConfidenceBar;
