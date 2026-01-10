"""Transaction Context Agent - Analyzes signals from transaction data."""
from datetime import datetime
from typing import Any

from app.orchestration.state import GraphState
from app.core.logging import log_agent_event


def extract_hour(timestamp: str) -> int:
    """Extract hour from ISO-8601 timestamp."""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.hour
    except (ValueError, AttributeError):
        return 12  # Default to noon if parsing fails


def run_transaction_context_agent(state: GraphState) -> GraphState:
    """
    Transaction Context Agent: Analyzes transaction against customer behavior.
    
    Calculates:
    - amount_ratio: amount / usual_amount_avg
    - hour_outside: whether hour is outside usual range
    - new_country: whether country is not in usual countries
    - new_device: whether device is not in usual devices
    
    Generates signals based on thresholds.
    """
    consolidated = state["consolidated"]
    
    # Extract values
    amount = consolidated["amount"]
    usual_amount_avg = consolidated["usual_amount_avg"]
    country = consolidated["country"]
    device_id = consolidated["device_id"]
    timestamp = consolidated["timestamp"]
    usual_hours_start = consolidated["usual_hours_start"]
    usual_hours_end = consolidated["usual_hours_end"]
    usual_countries = consolidated["usual_countries"]
    usual_devices = consolidated["usual_devices"]
    
    # Calculate metrics
    hour = extract_hour(timestamp)
    
    # Amount ratio (avoid division by zero)
    if usual_amount_avg > 0:
        amount_ratio = amount / usual_amount_avg
    else:
        amount_ratio = 999.0
    
    # Hour outside usual range
    hour_outside = hour < usual_hours_start or hour > usual_hours_end
    
    # New country check
    new_country = country not in usual_countries
    
    # New device check
    new_device = device_id not in usual_devices
    
    # Update metrics
    metrics = state["metrics"].copy()
    metrics.update({
        "amount_ratio": round(amount_ratio, 2),
        "hour": hour,
        "hour_outside": hour_outside,
        "new_country": new_country,
        "new_device": new_device,
    })
    
    # Generate signals
    signals = list(state["signals"])
    
    if amount_ratio > 3:
        signals.append("Monto fuera de rango")
    
    if hour_outside:
        signals.append("Horario no habitual")
    
    if new_country:
        signals.append("País no habitual")
    
    if new_device:
        signals.append("Dispositivo nuevo")
    
    log_agent_event(
        agent="TransactionContext",
        message=f"Analyzed transaction, found {len(signals)} signals",
        transaction_id=state["transaction_id"],
        amount_ratio=amount_ratio,
        hour_outside=hour_outside
    )
    
    return {
        **state,
        "metrics": metrics,
        "signals": signals,
    }
