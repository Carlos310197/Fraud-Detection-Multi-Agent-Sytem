"""Behavioral Pattern Agent - Computes behavioral risk score."""
from app.orchestration.state import GraphState
from app.core.logging import log_agent_event


def run_behavioral_pattern_agent(state: GraphState) -> GraphState:
    """
    Behavioral Pattern Agent: Computes a risk score based on behavioral patterns.
    
    Risk score calculation:
    - +0.35 if amount_ratio > 5
    - +0.25 if amount_ratio > 3 (but ≤ 5)
    - +0.15 if amount_ratio > 2 (but ≤ 3)
    - +0.15 if hour_outside
    - +0.20 if new_device
    - +0.25 if new_country
    """
    metrics = state["metrics"].copy()
    
    amount_ratio = metrics.get("amount_ratio", 1.0)
    hour_outside = metrics.get("hour_outside", False)
    new_device = metrics.get("new_device", False)
    new_country = metrics.get("new_country", False)
    
    # Calculate behavior risk score
    behavior_risk = 0.0
    
    # Amount ratio contribution
    if amount_ratio > 5:
        behavior_risk += 0.35
    elif amount_ratio > 3:
        behavior_risk += 0.25
    elif amount_ratio > 2:
        behavior_risk += 0.15
    
    # Time-based risk
    if hour_outside:
        behavior_risk += 0.15
    
    # Device risk
    if new_device:
        behavior_risk += 0.20
    
    # Country risk
    if new_country:
        behavior_risk += 0.25
    
    # Cap at 1.0
    behavior_risk = min(1.0, behavior_risk)
    
    metrics["behavior_risk"] = round(behavior_risk, 2)
    
    log_agent_event(
        agent="BehavioralPattern",
        message=f"Computed behavior risk score: {behavior_risk:.2f}",
        transaction_id=state["transaction_id"],
        behavior_risk=behavior_risk
    )
    
    return {
        **state,
        "metrics": metrics,
    }
