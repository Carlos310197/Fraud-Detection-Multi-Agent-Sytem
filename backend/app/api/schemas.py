"""Pydantic schemas for the fraud detection API."""
from datetime import datetime
from typing import Literal, Any
from pydantic import BaseModel, Field


# ============ Input Data Models ============

class Transaction(BaseModel):
    """A financial transaction."""
    transaction_id: str
    customer_id: str
    amount: float
    currency: str
    country: str
    channel: str
    device_id: str
    timestamp: str  # ISO-8601
    merchant_id: str


class CustomerBehavior(BaseModel):
    """Customer behavioral profile."""
    customer_id: str
    usual_amount_avg: float
    usual_hours: str  # "08-20"
    usual_countries: list[str]  # Normalized to list
    usual_devices: list[str]    # Normalized to list


class FraudPolicy(BaseModel):
    """Internal fraud detection policy."""
    policy_id: str
    rule: str
    version: str


# ============ Consolidated Data ============

class ConsolidatedTransaction(BaseModel):
    """Transaction consolidated with customer behavior data."""
    transaction_id: str
    customer_id: str
    amount: float
    currency: str
    country: str
    channel: str
    device_id: str
    timestamp: str
    merchant_id: str
    # Customer behavior
    usual_amount_avg: float
    usual_hours_start: int
    usual_hours_end: int
    usual_countries: list[str]
    usual_devices: list[str]


# ============ Citation Models ============

class CitationInternal(BaseModel):
    """Citation to an internal policy."""
    policy_id: str
    chunk_id: str
    version: str


class CitationExternal(BaseModel):
    """Citation to an external source."""
    url: str
    summary: str


# ============ Decision Response ============

DecisionType = Literal["APPROVE", "CHALLENGE", "BLOCK", "ESCALATE_TO_HUMAN"]


class HitlInfo(BaseModel):
    """HITL requirement information."""
    required: bool
    reason: str


class DecisionResponse(BaseModel):
    """Final decision response for a transaction."""
    decision: DecisionType
    confidence: float = Field(ge=0.0, le=1.0)
    signals: list[str]
    citations_internal: list[CitationInternal]
    citations_external: list[CitationExternal]
    explanation_customer: str
    explanation_audit: str
    ai_summary: str  # Detailed Markdown report for transaction detail view
    hitl: HitlInfo = Field(default_factory=lambda: HitlInfo(required=False, reason=""))


# ============ Audit Trail ============

class AuditEvent(BaseModel):
    """Single audit event in the agent pipeline."""
    transaction_id: str
    run_id: str = "legacy"  # UUID for each analysis run, defaults to "legacy" for old events
    seq: int
    ts: str  # ISO-8601 UTC
    duration_ms: float = 0.0  # Execution duration in milliseconds, defaults to 0 for old events
    agent: str
    input_summary: str
    output_summary: str
    output_json: dict[str, Any]


# ============ Human-in-the-Loop ============

class HitlCase(BaseModel):
    """Human-in-the-loop review case."""
    case_id: str
    transaction_id: str
    status: Literal["OPEN", "RESOLVED"]
    reason: str
    created_at: str  # ISO-8601 UTC
    resolved_at: str | None = None
    resolution: dict[str, Any] | None = None


class HitlResolution(BaseModel):
    """Request body for resolving a HITL case."""
    decision: DecisionType
    notes: str


# ============ API Request/Response Models ============

class IngestResponse(BaseModel):
    """Response from the ingest endpoint."""
    transactions_loaded: int
    customers_loaded: int
    policies_loaded: int


class AnalyzeAllResponse(BaseModel):
    """Response from analyze-all endpoint."""
    analyzed: int
    results: list[DecisionResponse]


class TransactionSummary(BaseModel):
    """Summary of a transaction for list views."""
    transaction_id: str
    customer_id: str
    amount: float
    currency: str
    timestamp: str
    decision: DecisionType | None = None
    confidence: float | None = None


class TransactionDetailResponse(BaseModel):
    """Full transaction details with analysis results."""
    transaction: Transaction
    customer_behavior: CustomerBehavior | None
    latest_decision: DecisionResponse | None
    audit_events: list[AuditEvent]


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str | None = None
