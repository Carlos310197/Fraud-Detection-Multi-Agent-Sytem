import React from 'react';
import { LinearProgress, Box } from '@mui/material';
import { useIsFetching, useIsMutating } from '@tanstack/react-query';

export const GlobalLoadingIndicator: React.FC = () => {
  const isFetching = useIsFetching();
  const isMutating = useIsMutating();
  
  const isLoading = isFetching > 0 || isMutating > 0;

  if (!isLoading) return null;

  return (
    <Box sx={{ width: '100%', position: 'fixed', top: 64, left: 0, zIndex: 1300 }}>
      <LinearProgress />
    </Box>
  );
};
