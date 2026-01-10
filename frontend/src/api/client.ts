/// <reference types="vite/client" />
/**
 * API client for the Fraud Detection backend
 */
import axios from 'axios';
import type {
  IngestResponse,
  TransactionSummary,
  TransactionDetail,
  DecisionResponse,
  HitlCase,
  HitlResolution,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Ingest data from files into the system
 */
export async function ingest(): Promise<IngestResponse> {
  const response = await api.post<IngestResponse>('/ingest');
  return response.data;
}

/**
 * List all transactions
 */
export async function listTransactions(): Promise<TransactionSummary[]> {
  const response = await api.get<TransactionSummary[]>('/transactions');
  return response.data;
}

/**
 * Analyze a transaction
 */
export async function analyzeTransaction(transactionId: string): Promise<DecisionResponse> {
  const response = await api.post<DecisionResponse>(`/transactions/${transactionId}/analyze`);
  return response.data;
}

/**
 * Analyze all pending transactions (those without decisions)
 */
export async function analyzeAllPending(): Promise<{ analyzed: number; results: DecisionResponse[] }> {
  const response = await api.post<{ analyzed: number; results: DecisionResponse[] }>('/transactions/analyze-all');
  return response.data;
}

/**
 * Get transaction details
 */
export async function getTransaction(transactionId: string): Promise<TransactionDetail> {
  const response = await api.get<TransactionDetail>(`/transactions/${transactionId}`);
  return response.data;
}

/**
 * List open HITL cases
 */
export async function listHitlCases(): Promise<HitlCase[]> {
  const response = await api.get<HitlCase[]>('/hitl');
  return response.data;
}

/**
 * Resolve a HITL case
 */
export async function resolveHitlCase(
  caseId: string,
  resolution: HitlResolution
): Promise<HitlCase> {
  const response = await api.post<HitlCase>(`/hitl/${caseId}/resolve`, resolution);
  return response.data;
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{ status: string; timestamp: string }> {
  const response = await api.get<{ status: string; timestamp: string }>('/health');
  return response.data;
}

export default api;
