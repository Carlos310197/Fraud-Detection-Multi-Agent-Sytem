"""Evidence Aggregation Agent - Consolidates all evidence."""
from app.orchestration.state import GraphState
from app.core.logging import log_agent_event


def run_evidence_aggregation_agent(state: GraphState) -> GraphState:
    """
    Evidence Aggregation Agent: Consolidates all collected evidence.
    
    Creates an evidence summary containing:
    - signals
    - metrics
    - citations_internal
    - citations_external
    """
    evidence = {
        "signals": state["signals"],
        "metrics": state["metrics"],
        "citations_internal": state["citations_internal"],
        "citations_external": state["citations_external"],
    }
    
    log_agent_event(
        agent="EvidenceAggregation",
        message=f"Aggregated evidence: {len(state['signals'])} signals, "
                f"{len(state['citations_internal'])} internal citations, "
                f"{len(state['citations_external'])} external citations",
        transaction_id=state["transaction_id"]
    )
    
    return {
        **state,
        "evidence": evidence,
    }
