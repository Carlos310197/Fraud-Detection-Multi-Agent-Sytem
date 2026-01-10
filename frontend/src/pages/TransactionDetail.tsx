import React from 'react';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Box,
  Button,
  Typography,
  Paper,
  Grid,
  Chip,
  Card,
  CardContent,
  Alert,
  CircularProgress,
  Breadcrumbs,
  Link,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import WarningIcon from '@mui/icons-material/Warning';
import { getTransaction, analyzeTransaction } from '../api/client';
import type { DecisionType } from '../types';
import SignalsChips from '../components/SignalsChips';
import ConfidenceBar from '../components/ConfidenceBar';
import AuditTimeline from '../components/AuditTimeline';

const getDecisionColor = (decision: DecisionType): 'success' | 'warning' | 'error' | 'info' => {
  switch (decision) {
    case 'APPROVE': return 'success';
    case 'CHALLENGE': return 'warning';
    case 'BLOCK': return 'error';
    case 'ESCALATE_TO_HUMAN': return 'info';
  }
};

const getDecisionLabel = (decision: DecisionType): string => {
  switch (decision) {
    case 'APPROVE': return 'Aprobada';
    case 'CHALLENGE': return 'Requiere Validación';
    case 'BLOCK': return 'Bloqueada';
    case 'ESCALATE_TO_HUMAN': return 'Revisión Humana';
  }
};

export const TransactionDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['transaction', id],
    queryFn: () => getTransaction(id!),
    enabled: !!id,
  });

  const analyzeMutation = useMutation({
    mutationFn: analyzeTransaction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transaction', id] });
    },
  });

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !data) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Error al cargar la transacción: {String(error)}
        </Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/')} sx={{ mt: 2 }}>
          Volver
        </Button>
      </Box>
    );
  }

  const { transaction, customer_behavior, latest_decision, audit_events } = data;

  return (
    <Box sx={{ p: 3 }}>
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link component={RouterLink} to="/" underline="hover" color="inherit">
          Transacciones
        </Link>
        <Typography color="text.primary">{transaction.transaction_id}</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1">
            Transacción {transaction.transaction_id}
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Cliente: {transaction.customer_id}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          {latest_decision?.hitl?.required && (
            <Button
              variant="contained"
              color="warning"
              startIcon={<WarningIcon />}
              component={RouterLink}
              to="/hitl"
            >
              Ver en Cola HITL
            </Button>
          )}
          <Button
            variant="contained"
            startIcon={<PlayArrowIcon />}
            onClick={() => analyzeMutation.mutate(id!)}
            disabled={analyzeMutation.isPending}
          >
            {analyzeMutation.isPending ? 'Analizando...' : 'Re-analizar'}
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Decision Summary */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            {latest_decision ? (
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  <Chip
                    label={getDecisionLabel(latest_decision.decision)}
                    color={getDecisionColor(latest_decision.decision)}
                    sx={{ fontSize: '1rem', py: 2, px: 1 }}
                  />
                  <Typography variant="h6">
                    Riesgo de Fraude: {Math.round(latest_decision.confidence * 100)}%
                  </Typography>
                </Box>
                <ConfidenceBar confidence={latest_decision.confidence} />
              </Box>
            ) : (
              <Alert severity="info">
                Esta transacción aún no ha sido analizada. Haz clic en "Analizar" para procesarla.
              </Alert>
            )}
          </Paper>
        </Grid>

        {/* Explanations Box - Customer + Audit */}
        {latest_decision && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Resultado del Análisis
                </Typography>
                
                <Box sx={{ mb: 3, p: 2, bgcolor: 'primary.50', borderRadius: 1, border: 1, borderColor: 'primary.200' }}>
                  <Typography variant="subtitle2" gutterBottom color="primary.main" fontWeight="bold">
                    Explicación para el Cliente
                  </Typography>
                  <Typography variant="body1">
                    {latest_decision.explanation_customer}
                  </Typography>
                </Box>

                <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1, border: 1, borderColor: 'grey.300' }}>
                  <Typography variant="subtitle2" gutterBottom color="text.secondary" fontWeight="bold">
                    Resumen de Auditoría
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {latest_decision.explanation_audit}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Transaction Details */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Detalles de la Transacción
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">Monto</Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {transaction.amount.toLocaleString('es-PE')} {transaction.currency}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">País</Typography>
                  <Typography variant="body1">{transaction.country}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">Canal</Typography>
                  <Typography variant="body1">{transaction.channel}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">Dispositivo</Typography>
                  <Typography variant="body1">{transaction.device_id}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">Merchant</Typography>
                  <Typography variant="body1">{transaction.merchant_id}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">Timestamp</Typography>
                  <Typography variant="body1">
                    {new Date(transaction.timestamp).toLocaleString('es-PE')}
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Customer Behavior */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Comportamiento Habitual
              </Typography>
              {customer_behavior ? (
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">Monto Promedio</Typography>
                    <Typography variant="body1" fontWeight="medium">
                      {customer_behavior.usual_amount_avg.toLocaleString('es-PE')} PEN
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">Horario Habitual</Typography>
                    <Typography variant="body1">{customer_behavior.usual_hours}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">Países</Typography>
                    <Typography variant="body1">{customer_behavior.usual_countries.join(', ')}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">Dispositivos</Typography>
                    <Typography variant="body1">{customer_behavior.usual_devices.join(', ')}</Typography>
                  </Grid>
                </Grid>
              ) : (
                <Alert severity="warning">No hay datos de comportamiento disponibles.</Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Signals */}
        {latest_decision && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Señales Detectadas
                </Typography>
                <SignalsChips signals={latest_decision.signals} />
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* AI Summary - Detailed Report */}
        {latest_decision && latest_decision.ai_summary && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Informe Detallado de IA
                </Typography>
                <Box
                  sx={{
                    '& h1': { fontSize: '1.25rem', fontWeight: 700, margin: '0.5rem 0' },
                    '& h2': { fontSize: '1.1rem', fontWeight: 700, margin: '0.5rem 0' },
                    '& p': { margin: '0.5rem 0' },
                    '& ul': { paddingLeft: '1.25rem', margin: '0.5rem 0' },
                    '& li': { marginBottom: '0.25rem' },
                    '& code': { fontFamily: 'monospace' },
                  }}
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {latest_decision.ai_summary}
                  </ReactMarkdown>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Audit Trail */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Audit Trail
              </Typography>
              <AuditTimeline events={audit_events} />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default TransactionDetail;
