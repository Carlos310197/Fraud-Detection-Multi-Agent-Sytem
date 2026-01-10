import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Typography,
  Paper,
  Chip,
  Alert,
  Snackbar,
  CircularProgress,
  Drawer,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Card,
  CardContent,
  Grid,
  IconButton,
} from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import RefreshIcon from '@mui/icons-material/Refresh';
import CloseIcon from '@mui/icons-material/Close';
import CheckIcon from '@mui/icons-material/Check';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { listHitlCases, resolveHitlCase, getTransaction } from '../api/client';
import type { HitlCase, DecisionType } from '../types';

export const HitlQueue: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [resolution, setResolution] = useState<{ decision: DecisionType; notes: string }>({
    decision: 'APPROVE',
    notes: '',
  });
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  // Auto-refresh every 10 seconds
  const { data: cases, isLoading, error, refetch } = useQuery({
    queryKey: ['hitl-cases'],
    queryFn: listHitlCases,
    refetchInterval: 10000,
  });

  const selectedCase = cases?.find(c => c.case_id === selectedCaseId);

  // Fetch transaction detail only when a case is selected
  const { data: transactionDetail } = useQuery({
    queryKey: ['transaction', selectedCase?.transaction_id],
    queryFn: () => getTransaction(selectedCase!.transaction_id),
    enabled: !!selectedCase,
  });

  const resolveMutation = useMutation({
    mutationFn: ({ caseId, resolution }: { caseId: string; resolution: { decision: DecisionType; notes: string } }) =>
      resolveHitlCase(caseId, resolution),
    onSuccess: (_, { caseId }) => {
      setSnackbar({
        open: true,
        message: `Caso ${caseId} resuelto exitosamente`,
        severity: 'success',
      });
      setSelectedCaseId(null);
      queryClient.invalidateQueries({ queryKey: ['hitl-cases'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
    onError: (err) => {
      setSnackbar({
        open: true,
        message: `Error al resolver caso: ${err}`,
        severity: 'error',
      });
    },
  });

  const handleOpenCase = (hitlCase: HitlCase) => {
    setSelectedCaseId(hitlCase.case_id);
    setResolution({ decision: 'APPROVE', notes: '' });
  };

  const handleResolve = () => {
    if (selectedCase) {
      resolveMutation.mutate({
        caseId: selectedCase.case_id,
        resolution,
      });
    }
  };

  const columns: GridColDef[] = [
    { field: 'case_id', headerName: 'ID Caso', flex: 1, minWidth: 150 },
    {
      field: 'transaction_id',
      headerName: 'Transacción',
      flex: 1,
      minWidth: 130,
      renderCell: (params: GridRenderCellParams) => (
        <Button
          variant="text"
          size="small"
          endIcon={<OpenInNewIcon fontSize="small" />}
          component={RouterLink}
          to={`/transactions/${params.value}`}
        >
          {params.value}
        </Button>
      ),
    },
    { field: 'reason', headerName: 'Razón', flex: 2, minWidth: 200 },
    {
      field: 'status',
      headerName: 'Estado',
      flex: 0.8,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={params.value === 'OPEN' ? 'Abierto' : 'Resuelto'}
          color={params.value === 'OPEN' ? 'warning' : 'success'}
          size="small"
        />
      ),
    },
    {
      field: 'created_at',
      headerName: 'Creado',
      flex: 1.2,
      minWidth: 180,
      valueFormatter: (params) => new Date(params.value).toLocaleString('es-PE'),
    },
    {
      field: 'actions',
      headerName: 'Acciones',
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params: GridRenderCellParams<HitlCase>) => (
        <Button
          size="small"
          variant="contained"
          startIcon={<CheckIcon />}
          onClick={() => handleOpenCase(params.row)}
          disabled={params.row.status === 'RESOLVED'}
        >
          Resolver
        </Button>
      ),
    },
  ];

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Cola HITL (Human-in-the-Loop)
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={() => refetch()}
        >
          Actualizar
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Error al cargar casos: {String(error)}
        </Alert>
      )}

      {cases && cases.length === 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          No hay casos pendientes de revisión humana.
        </Alert>
      )}

      <Paper sx={{ height: 500, width: '100%' }}>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <CircularProgress />
          </Box>
        ) : (
          <DataGrid
            rows={cases || []}
            columns={columns}
            getRowId={(row) => row.case_id}
            pageSizeOptions={[10, 25, 50]}
            initialState={{
              pagination: { paginationModel: { pageSize: 10 } },
            }}
            disableRowSelectionOnClick
          />
        )}
      </Paper>

      {/* Resolution Drawer */}
      <Drawer
        anchor="right"
        open={!!selectedCase}
        onClose={() => {
          setSelectedCaseId(null);
        }}
        PaperProps={{ sx: { width: { xs: '100%', sm: 500 } } }}
      >
        {selectedCase && (
          <Box sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6">
                Resolver Caso {selectedCase.case_id}
              </Typography>
              <IconButton onClick={() => setSelectedCaseId(null)}>
                <CloseIcon />
              </IconButton>
            </Box>

            {/* Case Info */}
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Información del Caso
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">Transacción</Typography>
                    <Typography variant="body1">{selectedCase.transaction_id}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">Razón</Typography>
                    <Typography variant="body1">{selectedCase.reason}</Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="body2" color="text.secondary">Creado</Typography>
                    <Typography variant="body1">
                      {new Date(selectedCase.created_at).toLocaleString('es-PE')}
                    </Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>

            {/* Transaction Summary */}
            {transactionDetail && (
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>
                    Resumen de Transacción
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">Monto</Typography>
                      <Typography variant="body1" fontWeight="medium">
                        {transactionDetail.transaction.amount.toLocaleString('es-PE')} {transactionDetail.transaction.currency}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">País</Typography>
                      <Typography variant="body1">{transactionDetail.transaction.country}</Typography>
                    </Grid>
                    {transactionDetail.latest_decision && (
                      <>
                        <Grid item xs={12}>
                          <Typography variant="body2" color="text.secondary">Señales</Typography>
                          <Box sx={{ mt: 0.5 }}>
                            {transactionDetail.latest_decision.signals.map((signal, idx) => (
                              <Chip key={idx} label={signal} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                            ))}
                          </Box>
                        </Grid>
                        <Grid item xs={12}>
                          <Typography variant="body2" color="text.secondary">Confianza</Typography>
                          <Typography variant="body1">
                            {Math.round(transactionDetail.latest_decision.confidence * 100)}%
                          </Typography>
                        </Grid>
                      </>
                    )}
                  </Grid>
                </CardContent>
              </Card>
            )}

            {/* Resolution Form */}
            <Typography variant="subtitle2" gutterBottom>
              Resolución
            </Typography>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Decisión</InputLabel>
              <Select
                value={resolution.decision}
                label="Decisión"
                onChange={(e) => setResolution({ ...resolution, decision: e.target.value as DecisionType })}
              >
                <MenuItem value="APPROVE">Aprobar</MenuItem>
                <MenuItem value="CHALLENGE">Challenge (Validación adicional)</MenuItem>
                <MenuItem value="BLOCK">Bloquear</MenuItem>
              </Select>
            </FormControl>
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Notas de resolución"
              value={resolution.notes}
              onChange={(e) => setResolution({ ...resolution, notes: e.target.value })}
              sx={{ mb: 3 }}
            />
            <Button
              fullWidth
              variant="contained"
              size="large"
              startIcon={<CheckIcon />}
              onClick={handleResolve}
              disabled={resolveMutation.isPending || !resolution.notes.trim()}
            >
              {resolveMutation.isPending ? 'Procesando...' : 'Confirmar Resolución'}
            </Button>
          </Box>
        )}
      </Drawer>

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

export default HitlQueue;
