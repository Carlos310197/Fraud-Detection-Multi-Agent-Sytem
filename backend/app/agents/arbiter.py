"""Decision Arbiter Agent - Makes the final decision."""
from app.orchestration.state import GraphState
from app.core.logging import log_agent_event


def run_arbiter_agent(state: GraphState) -> GraphState:
    """
    Decision Arbiter Agent: Makes the final fraud decision.
    
    Score calculation:
    - Base score = behavior_risk
    - +0.20 if external citations exist
    
    Confidence adjustments:
    - + pro_fraud.confidence_delta
    - - pro_customer.confidence_delta
    
    Decision rules (in order):
    1) If policy_hint == "ESCALATE_TO_HUMAN" AND new_country AND new_device → ESCALATE_TO_HUMAN
    2) If confidence >= 0.75 AND "Alerta externa" AND amount_ratio > 3 → BLOCK
    3) If amount_ratio > 3 AND hour_outside → CHALLENGE
    4) If confidence < 0.45 AND signals <= 1 → APPROVE
    5) Default: confidence >= 0.60 → CHALLENGE, else → ESCALATE_TO_HUMAN
    
    HITL triggers:
    - decision == ESCALATE_TO_HUMAN
    - 0.45 <= confidence <= 0.60
    """
    metrics = state["metrics"]
    signals = state["signals"]
    debate = state["debate"]
    citations_external = state["citations_external"]
    
    # Extract values
    behavior_risk = metrics.get("behavior_risk", 0.0)
    policy_hint = metrics.get("policy_hint")
    amount_ratio = metrics.get("amount_ratio", 1.0)
    hour_outside = metrics.get("hour_outside", False)
    new_country = metrics.get("new_country", False)
    new_device = metrics.get("new_device", False)
    
    has_external_alert = "Alerta externa" in signals
    
    # Calculate base confidence
    confidence = behavior_risk
    
    # Add external hit bonus
    if citations_external:
        confidence += 0.20
    
    # Apply debate adjustments
    pro_fraud_delta = debate["pro_fraud"].get("confidence_delta", 0.0)
    pro_customer_delta = debate["pro_customer"].get("confidence_delta", 0.0)
    
    confidence += pro_fraud_delta
    confidence -= pro_customer_delta
    
    # Clamp confidence to [0, 1]
    confidence = max(0.0, min(1.0, confidence))
    
    # Decision rules (strict order)
    decision = None
    
    # Rule 1: Escalate on policy hint with new country/device
    if policy_hint == "ESCALATE_TO_HUMAN" and new_country and new_device:
        decision = "ESCALATE_TO_HUMAN"
    
    # Rule 2: Block on high confidence with external alert
    elif confidence >= 0.75 and has_external_alert and amount_ratio > 3:
        decision = "BLOCK"
    
    # Rule 3: Challenge on amount + hour issues
    elif amount_ratio > 3 and hour_outside:
        decision = "CHALLENGE"
    
    # Rule 4: Approve on low confidence with few signals
    elif confidence < 0.45 and len(signals) <= 1:
        decision = "APPROVE"
    
    # Rule 5: Default based on confidence
    else:
        if confidence >= 0.60:
            decision = "CHALLENGE"
        else:
            decision = "ESCALATE_TO_HUMAN"
    
    # HITL determination
    hitl_required = False
    hitl_reason = ""
    
    if decision == "ESCALATE_TO_HUMAN":
        hitl_required = True
        hitl_reason = "Política o baja confianza requiere revisión humana"
    elif 0.45 <= confidence <= 0.60:
        hitl_required = True
        hitl_reason = "Nivel de confianza límite requiere evaluación manual"
    
    # Output fraud_risk as confidence (industry standard)
    # Confidence = fraud risk score [0-1]
    # Decision thresholds:
    #   < 0.45: APPROVE (low risk)
    #   0.45-0.75: CHALLENGE/ESCALATE (needs review)
    #   >= 0.75: BLOCK (high risk)
    output_confidence = confidence
    
    # Calculate additional metrics for audit trail
    decision_uncertainty = abs(0.5 - confidence) * 2  # How far from borderline
    
    log_agent_event(
        agent="Arbiter",
        message=f"Decision: {decision}, fraud_risk: {output_confidence:.2f}, HITL: {hitl_required}",
        transaction_id=state["transaction_id"],
        decision=decision,
        confidence=output_confidence,
        hitl_required=hitl_required
    )
    
    return {
        **state,
        "decision": decision,
        "confidence": round(output_confidence, 2),
        "hitl": {
            "required": hitl_required,
            "reason": hitl_reason,
        },
    }
