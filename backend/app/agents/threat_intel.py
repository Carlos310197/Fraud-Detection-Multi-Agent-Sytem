"""External Threat Intel Agent - Searches for external threat information."""
from app.orchestration.state import GraphState
from app.web.governed_search import GovernedSearchService
from app.core.logging import log_agent_event


def run_threat_intel_agent(
    state: GraphState,
    search_service: GovernedSearchService
) -> GraphState:
    """
    External Threat Intel Agent: Searches for external threat intelligence.
    
    Query format: "fraud alert {merchant_id} {country}"
    
    If results are found, adds "Alerta externa" signal.
    """
    consolidated = state["consolidated"]
    merchant_id = consolidated.get("merchant_id", "")
    country = consolidated.get("country", "")
    
    # Build search query
    query = f"fraud alert {merchant_id} {country}"
    
    # Execute governed search
    results = search_service.search(query)
    
    # Update state
    signals = list(state["signals"])
    
    if results:
        signals.append("Alerta externa")
    
    log_agent_event(
        agent="ThreatIntel",
        message=f"Web search returned {len(results)} results",
        transaction_id=state["transaction_id"],
        query=query,
        results_count=len(results)
    )
    
    return {
        **state,
        "citations_external": results,
        "signals": signals,
    }
