import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Typography,
  Alert,
  Snackbar,
  Chip,
  Paper,
  CircularProgress,
} from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import RefreshIcon from '@mui/icons-material/Refresh';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PlaylistPlayIcon from '@mui/icons-material/PlaylistPlay';
import UploadIcon from '@mui/icons-material/Upload';
import { listTransactions, ingest, analyzeTransaction, analyzeAllPending } from '../api/client';
import type { TransactionSummary, DecisionType } from '../types';

const getDecisionColor = (decision: DecisionType | null): 'success' | 'warning' | 'error' | 'info' | 'default' => {
  switch (decision) {
    case 'APPROVE': return 'success';
    case 'CHALLENGE': return 'warning';
    case 'BLOCK': return 'error';
    case 'ESCALATE_TO_HUMAN': return 'info';
    default: return 'default';
  }
};

const getDecisionLabel = (decision: DecisionType | null): string => {
  if (!decision) return 'Pendiente';
  switch (decision) {
    case 'APPROVE': return 'Aprobada';
    case 'CHALLENGE': return 'Requiere Validación';
    case 'BLOCK': return 'Bloqueada';
    case 'ESCALATE_TO_HUMAN': return 'Revisión Humana';
  }
};

export const Transactions: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const { data: transactions, isLoading, error, refetch } = useQuery({
    queryKey: ['transactions'],
    queryFn: listTransactions,
  });

  const ingestMutation = useMutation({
    mutationFn: ingest,
    onSuccess: (data) => {
      setSnackbar({
        open: true,
        message: `Datos cargados: ${data.transactions_loaded} transacciones, ${data.customers_loaded} clientes, ${data.policies_loaded} políticas`,
        severity: 'success',
      });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
    onError: (err) => {
      setSnackbar({
        open: true,
        message: `Error al cargar datos: ${err}`,
        severity: 'error',
      });
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: analyzeTransaction,
    onMutate: (transactionId) => {
      setAnalyzingId(transactionId);
    },
    onSuccess: (_, transactionId) => {
      setSnackbar({
        open: true,
        message: `Análisis completado para ${transactionId}`,
        severity: 'success',
      });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
    onError: (err, transactionId) => {
      setSnackbar({
        open: true,
        message: `Error al analizar ${transactionId}: ${err}`,
        severity: 'error',
      });
    },
    onSettled: () => {
      setAnalyzingId(null);
    },
  });

  const analyzeAllMutation = useMutation({
    mutationFn: analyzeAllPending,
    onSuccess: (data) => {
      setSnackbar({
        open: true,
        message: `Análisis masivo completado: ${data.analyzed} transacciones procesadas`,
        severity: 'success',
      });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
    onError: (err) => {
      setSnackbar({
        open: true,
        message: `Error en análisis masivo: ${err}`,
        severity: 'error',
      });
    },
  });

  const pendingCount = transactions?.filter(t => !t.decision).length || 0;

  const columns: GridColDef[] = [
    { 
      field: 'transaction_id', 
      headerName: 'ID Transacción', 
      flex: 1,
      minWidth: 130,
      renderCell: (params: GridRenderCellParams) => (
        <Button
          variant="text"
          size="small"
          onClick={() => navigate(`/transactions/${params.value}`)}
        >
          {params.value}
        </Button>
      ),
    },
    { field: 'customer_id', headerName: 'Cliente', flex: 0.8, minWidth: 100 },
    { 
      field: 'amount', 
      headerName: 'Monto', 
      flex: 1,
      minWidth: 120,
      valueGetter: (params) => `${params.value?.toLocaleString('es-PE')} ${params.row.currency || ''}`,
    },
    { field: 'timestamp', headerName: 'Fecha/Hora', flex: 1.2, minWidth: 180 },
    {
      field: 'decision',
      headerName: 'Decisión',
      flex: 1.2,
      minWidth: 160,
      renderCell: (params: GridRenderCellParams) => (
        <Chip 
          label={getDecisionLabel(params.value)}
          color={getDecisionColor(params.value)}
          size="small"
          variant={params.value ? 'filled' : 'outlined'}
        />
      ),
    },
    {
      field: 'confidence',
      headerName: 'Confianza',
      flex: 0.8,
      minWidth: 100,
      valueFormatter: (params) => params.value !== null ? `${Math.round(params.value * 100)}%` : '-',
    },
    {
      field: 'actions',
      headerName: 'Acciones',
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params: GridRenderCellParams<TransactionSummary>) => {
        const isAnalyzing = analyzingId === params.row.transaction_id;
        const isBulkAnalyzing = analyzeAllMutation.isPending;
        const isDisabled = isAnalyzing || isBulkAnalyzing;
        return (
          <Button
            size="small"
            startIcon={isAnalyzing ? <CircularProgress size={16} /> : <PlayArrowIcon />}
            onClick={() => analyzeMutation.mutate(params.row.transaction_id)}
            disabled={isDisabled}
          >
            {isAnalyzing ? 'Analizando...' : 'Analizar'}
          </Button>
        );
      },
    },
  ];

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Transacciones
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            startIcon={<UploadIcon />}
            onClick={() => ingestMutation.mutate()}
            disabled={ingestMutation.isPending}
          >
            {ingestMutation.isPending ? 'Cargando...' : 'Cargar Datos'}
          </Button>
          <Button
            variant="contained"
            color="secondary"
            startIcon={analyzeAllMutation.isPending ? <CircularProgress size={20} color="inherit" /> : <PlaylistPlayIcon />}
            onClick={() => analyzeAllMutation.mutate()}
            disabled={analyzeAllMutation.isPending || pendingCount === 0}
          >
            {analyzeAllMutation.isPending ? 'Analizando...' : `Analizar Pendientes (${pendingCount})`}
          </Button>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => refetch()}
          >
            Actualizar
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Error al cargar transacciones: {String(error)}
        </Alert>
      )}

      <Paper sx={{ height: 500, width: '100%' }}>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <CircularProgress />
          </Box>
        ) : (
          <DataGrid
            rows={transactions || []}
            columns={columns}
            getRowId={(row) => row.transaction_id}
            pageSizeOptions={[10, 25, 50]}
            initialState={{
              pagination: { paginationModel: { pageSize: 10 } },
              sorting: { sortModel: [{ field: 'timestamp', sort: 'desc' }] },
            }}
            disableRowSelectionOnClick
            slots={{
              toolbar: () => null,
            }}
            slotProps={{
              toolbar: {
                showQuickFilter: true,
                quickFilterProps: { debounceMs: 500 },
              },
            }}
          />
        )}
      </Paper>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Transactions;
