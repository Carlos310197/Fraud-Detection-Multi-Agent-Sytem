"""Graph state definition for the multi-agent orchestration."""
from typing import TypedDict, Any, Literal
from pydantic import BaseModel


class HITLState(TypedDict):
    """Human-in-the-loop state."""
    required: bool
    reason: str


class DebatePosition(TypedDict):
    """Single debate position state."""
    recommended_decision: str
    confidence_delta: float
    reasoning: str


class DebateState(TypedDict):
    """Debate agents state."""
    pro_fraud: DebatePosition
    pro_customer: DebatePosition


class GraphState(TypedDict):
    """
    Shared state for the multi-agent graph.
    
    This state flows through all agents and accumulates
    signals, evidence, and decisions.
    """
    # Transaction identification
    transaction_id: str
    
    # Consolidated transaction data
    consolidated: dict[str, Any]
    
    # Detected signals (list of strings)
    signals: list[str]
    
    # Computed metrics
    metrics: dict[str, Any]
    
    # Internal citations from RAG
    citations_internal: list[dict[str, str]]
    
    # External citations from web search
    citations_external: list[dict[str, str]]
    
    # Aggregated evidence
    evidence: dict[str, Any]
    
    # Debate positions
    debate: DebateState
    
    # Final decision
    decision: str | None
    
    # Confidence score
    confidence: float | None
    
    # Explanations
    explanation_customer: str | None
    explanation_audit: str | None
    ai_summary: str | None  # Detailed AI-generated report
    
    # HITL state
    hitl: HITLState


def create_initial_state(
    transaction_id: str,
    consolidated: dict[str, Any]
) -> GraphState:
    """
    Create the initial graph state for a transaction.
    
    Args:
        transaction_id: The transaction ID
        consolidated: Consolidated transaction data as dict
        
    Returns:
        Initial GraphState
    """
    return GraphState(
        transaction_id=transaction_id,
        consolidated=consolidated,
        signals=[],
        metrics={},
        citations_internal=[],
        citations_external=[],
        evidence={},
        debate={
            "pro_fraud": {"recommended_decision": "", "confidence_delta": 0.0, "reasoning": ""},
            "pro_customer": {"recommended_decision": "", "confidence_delta": 0.0, "reasoning": ""}
        },
        decision=None,
        confidence=None,
        explanation_customer=None,
        explanation_audit=None,
        ai_summary=None,
        hitl={"required": False, "reason": ""}
    )
