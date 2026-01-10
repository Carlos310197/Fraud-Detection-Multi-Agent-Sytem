import React from 'react';
import { Chip, Stack } from '@mui/material';

interface SignalsChipsProps {
  signals: string[];
}

const getSignalColor = (signal: string): 'error' | 'warning' | 'info' | 'default' => {
  const lowerSignal = signal.toLowerCase();
  if (lowerSignal.includes('alerta externa') || lowerSignal.includes('fraude')) {
    return 'error';
  }
  if (lowerSignal.includes('monto') || lowerSignal.includes('país')) {
    return 'warning';
  }
  if (lowerSignal.includes('horario') || lowerSignal.includes('dispositivo')) {
    return 'info';
  }
  return 'default';
};

export const SignalsChips: React.FC<SignalsChipsProps> = ({ signals }) => {
  if (!signals || signals.length === 0) {
    return <Chip label="Sin señales" color="success" size="small" />;
  }

  return (
    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
      {signals.map((signal, index) => (
        <Chip
          key={index}
          label={signal}
          color={getSignalColor(signal)}
          size="small"
          sx={{ mb: 0.5 }}
        />
      ))}
    </Stack>
  );
};

export default SignalsChips;
