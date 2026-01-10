/**
 * TypeScript types for the Fraud Detection API
 */

export type DecisionType = 'APPROVE' | 'CHALLENGE' | 'BLOCK' | 'ESCALATE_TO_HUMAN';

export interface CitationInternal {
  policy_id: string;
  chunk_id: string;
  version: string;
}

export interface CitationExternal {
  url: string;
  summary: string;
}

export interface HitlInfo {
  required: boolean;
  reason: string;
}

export interface DecisionResponse {
  decision: DecisionType;
  confidence: number;
  signals: string[];
  citations_internal: CitationInternal[];
  citations_external: CitationExternal[];
  explanation_customer: string;
  explanation_audit: string;
  ai_summary: string;
  hitl: HitlInfo;
}

export interface Transaction {
  transaction_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  country: string;
  channel: string;
  device_id: string;
  timestamp: string;
  merchant_id: string;
}

export interface CustomerBehavior {
  customer_id: string;
  usual_amount_avg: number;
  usual_hours: string;
  usual_countries: string[];
  usual_devices: string[];
}

export interface TransactionSummary {
  transaction_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  timestamp: string;
  decision: DecisionType | null;
  confidence: number | null;
}

export interface AuditEvent {
  transaction_id: string;
  run_id: string;
  seq: number;
  ts: string;
  duration_ms: number;
  agent: string;
  input_summary: string;
  output_summary: string;
  output_json: Record<string, unknown>;
}

export interface TransactionDetail {
  transaction: Transaction;
  customer_behavior: CustomerBehavior | null;
  latest_decision: DecisionResponse | null;
  audit_events: AuditEvent[];
}

export interface HitlCase {
  case_id: string;
  transaction_id: string;
  status: 'OPEN' | 'RESOLVED';
  reason: string;
  created_at: string;
  resolved_at: string | null;
  resolution: {
    decision: DecisionType;
    notes: string;
  } | null;
}

export interface IngestResponse {
  transactions_loaded: number;
  customers_loaded: number;
  policies_loaded: number;
}

export interface HitlResolution {
  decision: DecisionType;
  notes: string;
}
