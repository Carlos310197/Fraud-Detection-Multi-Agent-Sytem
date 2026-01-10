"""Internal Policy RAG Agent - Retrieves relevant policies."""
from typing import Any

from app.orchestration.state import GraphState
from app.rag.vector_store import VectorStore
from app.core.logging import log_agent_event


def run_policy_rag_agent(state: GraphState, vector_store: VectorStore) -> GraphState:
    """
    Internal Policy RAG Agent: Retrieves relevant fraud policies.
    
    Constructs a query from signals and metrics, then searches
    the vector store for matching policies.
    
    Also derives policy_hint from the retrieved rules:
    - "→ CHALLENGE" in rule → policy_hint = CHALLENGE
    - "→ ESCALATE_TO_HUMAN" in rule → policy_hint = ESCALATE_TO_HUMAN
    - "→ BLOCK" in rule → policy_hint = BLOCK
    """
    signals = state["signals"]
    metrics = state["metrics"]
    
    # Build query from signals and key metrics
    query_parts = signals.copy()
    
    if metrics.get("amount_ratio"):
        query_parts.append(f"amount_ratio={metrics['amount_ratio']}")
    if metrics.get("hour_outside"):
        query_parts.append("hour_outside=true")
    if metrics.get("new_country"):
        query_parts.append("new_country=true")
    if metrics.get("new_device"):
        query_parts.append("new_device=true")
    
    query = "; ".join(query_parts)
    
    # Query vector store
    results = vector_store.query(query, top_k=2)
    
    # Build citations
    citations_internal = []
    policy_hint = None
    
    for doc in results:
        citation = {
            "policy_id": doc.metadata.get("policy_id", ""),
            "chunk_id": doc.metadata.get("chunk_id", "1"),
            "version": doc.metadata.get("version", ""),
        }
        citations_internal.append(citation)
        
        # Derive policy hint from rule content
        content_upper = doc.content.upper()
        if "→ ESCALATE_TO_HUMAN" in doc.content or "ESCALATE_TO_HUMAN" in content_upper:
            if policy_hint is None or policy_hint != "ESCALATE_TO_HUMAN":
                policy_hint = "ESCALATE_TO_HUMAN"
        elif "→ BLOCK" in doc.content or "BLOCK" in content_upper:
            if policy_hint is None:
                policy_hint = "BLOCK"
        elif "→ CHALLENGE" in doc.content or "CHALLENGE" in content_upper:
            if policy_hint is None:
                policy_hint = "CHALLENGE"
    
    # Update metrics with policy hint
    updated_metrics = state["metrics"].copy()
    updated_metrics["policy_hint"] = policy_hint
    
    log_agent_event(
        agent="PolicyRAG",
        message=f"Retrieved {len(citations_internal)} policies, hint: {policy_hint}",
        transaction_id=state["transaction_id"],
        policy_hint=policy_hint
    )
    
    return {
        **state,
        "citations_internal": citations_internal,
        "metrics": updated_metrics,
    }
