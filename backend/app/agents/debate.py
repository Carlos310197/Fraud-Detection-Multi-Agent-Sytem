"""Debate Agents - Pro-Fraud and Pro-Customer advocates."""
from app.orchestration.state import GraphState, DebatePosition
from app.core.logging import log_agent_event
from app.core.llm import LLMService
from app.prompts import get_debate_pro_fraud_prompts, get_debate_pro_customer_prompts


def run_debate_pro_fraud_agent_mock(state: GraphState) -> GraphState:
    """Mock implementation of Pro-Fraud debate."""
    signals = state["signals"]
    metrics = state["metrics"]
    amount_ratio = metrics.get("amount_ratio", 1.0)
    
    has_external_alert = "Alerta externa" in signals
    has_amount_issue = "Monto fuera de rango" in signals
    has_hour_issue = "Horario no habitual" in signals
    
    if has_external_alert and amount_ratio > 3:
        recommended_decision = "BLOCK"
        reasoning = "Alta probabilidad de fraude: alerta externa detectada con monto significativamente elevado."
    elif has_amount_issue and has_hour_issue:
        recommended_decision = "CHALLENGE"
        reasoning = "Múltiples señales de riesgo: monto y horario fuera de patrones habituales."
    else:
        recommended_decision = "CHALLENGE"
        reasoning = "Señales de riesgo detectadas que requieren verificación adicional."
    
    signal_count = len(signals)
    if signal_count >= 3:
        confidence_delta = 0.05
    elif signal_count == 2:
        confidence_delta = 0.02
    else:
        confidence_delta = 0.00
    
    return recommended_decision, confidence_delta, reasoning


def run_debate_pro_fraud_agent_llm(state: GraphState, llm: LLMService) -> tuple[str, float, str]:
    """LLM-powered Pro-Fraud debate using YAML prompts."""
    signals = state["signals"]
    metrics = state["metrics"]
    consolidated = state["consolidated"]
    citations_external = state["citations_external"]
    citations_internal = state["citations_internal"]
    
    # Get prompts from YAML
    system_prompt, user_prompt = get_debate_pro_fraud_prompts(
        transaction_id=state["transaction_id"],
        amount=consolidated.get("amount", "N/A"),
        country=consolidated.get("country", "N/A"),
        channel=consolidated.get("channel", "N/A"),
        timestamp=consolidated.get("timestamp", "N/A"),
        signals=", ".join(signals) if signals else "Ninguna",
        amount_ratio=metrics.get("amount_ratio", 1.0),
        hour_outside=metrics.get("hour_outside", False),
        new_country=metrics.get("new_country", False),
        new_device=metrics.get("new_device", False),
        behavior_risk=metrics.get("behavior_risk", 0),
        policy_count=len(citations_internal),
        external_count=len(citations_external),
    )

    result = llm.generate_structured(
        prompt=user_prompt,
        schema={},
        system_prompt=system_prompt
    )
    
    return (
        result.get("recommended_decision", "CHALLENGE"),
        min(0.15, max(0.0, float(result.get("confidence_delta", 0.02)))),
        result.get("reasoning", "Análisis de fraude completado.")
    )


def run_debate_pro_fraud_agent(state: GraphState, llm: LLMService | None = None) -> GraphState:
    """
    Pro-Fraud Debate Agent: Argues for fraud detection.
    
    Uses LLM if provided, otherwise falls back to mock logic.
    """
    if llm:
        recommended_decision, confidence_delta, reasoning = run_debate_pro_fraud_agent_llm(state, llm)
    else:
        recommended_decision, confidence_delta, reasoning = run_debate_pro_fraud_agent_mock(state)
    
    pro_fraud: DebatePosition = {
        "recommended_decision": recommended_decision,
        "confidence_delta": confidence_delta,
        "reasoning": reasoning,
    }
    
    debate = state["debate"].copy()
    debate["pro_fraud"] = pro_fraud
    
    log_agent_event(
        agent="DebateProFraud",
        message=f"Recommends {recommended_decision} with delta {confidence_delta}",
        transaction_id=state["transaction_id"],
        recommended_decision=recommended_decision
    )
    
    return {
        **state,
        "debate": debate,
    }


def run_debate_pro_customer_agent_mock(state: GraphState) -> tuple[str, float, str]:
    """Mock implementation of Pro-Customer debate."""
    signals = state["signals"]
    has_external_alert = "Alerta externa" in signals
    
    minor_signals = {"Horario no habitual", "Dispositivo nuevo"}
    all_minor = all(s in minor_signals for s in signals)
    only_one_signal = len(signals) <= 1
    
    if only_one_signal and (len(signals) == 0 or all_minor):
        recommended_decision = "APPROVE"
        reasoning = "Bajo riesgo: señales menores que no justifican bloqueo o challenge."
    else:
        recommended_decision = "CHALLENGE"
        reasoning = "Aunque el cliente tiene historial limpio, las señales detectadas requieren verificación."
    
    if not has_external_alert:
        confidence_delta = 0.03
    else:
        confidence_delta = 0.00
    
    return recommended_decision, confidence_delta, reasoning


def run_debate_pro_customer_agent_llm(state: GraphState, llm: LLMService) -> tuple[str, float, str]:
    """LLM-powered Pro-Customer debate using YAML prompts."""
    signals = state["signals"]
    metrics = state["metrics"]
    consolidated = state["consolidated"]
    
    # Get prompts from YAML
    system_prompt, user_prompt = get_debate_pro_customer_prompts(
        transaction_id=state["transaction_id"],
        amount=consolidated.get("amount", "N/A"),
        country=consolidated.get("country", "N/A"),
        channel=consolidated.get("channel", "N/A"),
        timestamp=consolidated.get("timestamp", "N/A"),
        signals=", ".join(signals) if signals else "Ninguna",
        amount_ratio=metrics.get("amount_ratio", 1.0),
        hour_outside=metrics.get("hour_outside", False),
        new_country=metrics.get("new_country", False),
        new_device=metrics.get("new_device", False),
        behavior_risk=metrics.get("behavior_risk", 0),
        avg_amount=consolidated.get("usual_amount_avg", "N/A"),
        total_transactions=consolidated.get("total_transactions", "N/A"),
        usual_countries=consolidated.get("usual_countries", []),
    )

    result = llm.generate_structured(
        prompt=user_prompt,
        schema={},
        system_prompt=system_prompt
    )
    
    return (
        result.get("recommended_decision", "CHALLENGE"),
        min(0.05, max(0.0, float(result.get("confidence_delta", 0.02)))),
        result.get("reasoning", "Defensa del cliente completada.")
    )


def run_debate_pro_customer_agent(state: GraphState, llm: LLMService | None = None) -> GraphState:
    """
    Pro-Customer Debate Agent: Argues for customer legitimacy.
    
    Uses LLM if provided, otherwise falls back to mock logic.
    """
    if llm:
        recommended_decision, confidence_delta, reasoning = run_debate_pro_customer_agent_llm(state, llm)
    else:
        recommended_decision, confidence_delta, reasoning = run_debate_pro_customer_agent_mock(state)
    
    pro_customer: DebatePosition = {
        "recommended_decision": recommended_decision,
        "confidence_delta": confidence_delta,
        "reasoning": reasoning,
    }
    
    debate = state["debate"].copy()
    debate["pro_customer"] = pro_customer
    
    log_agent_event(
        agent="DebateProCustomer",
        message=f"Recommends {recommended_decision} with delta reduction {confidence_delta}",
        transaction_id=state["transaction_id"],
        recommended_decision=recommended_decision
    )
    
    return {
        **state,
        "debate": debate,
    }
