"""Explainability Agent - Generates human-readable explanations."""
from app.orchestration.state import GraphState
from app.core.logging import log_agent_event
from app.core.llm import LLMService
from app.prompts import get_customer_explanation_prompts, get_audit_explanation_prompts


def build_agent_path(transaction_id: str, audit_repo) -> str:
    """Build the agent execution path from audit events."""
    events = audit_repo.get_events(transaction_id)
    
    # Map agent names to friendly names
    agent_map = {
        "TransactionContext": "Context",
        "BehavioralPattern": "Behavior",
        "PolicyRAG": "RAG",
        "ThreatIntel": "Web",
        "EvidenceAggregation": "Evidence",
        "DebateProFraud": "Debate",
        "DebateProCustomer": "Debate",
        "Arbiter": "Decisión",
        "Explainability": "Explicación",
    }
    
    # Extract unique agent names in order (skip duplicates like both debate agents)
    seen = set()
    path_parts = []
    for event in events:
        agent_name = event.agent
        # Skip error events
        if "_error" in agent_name:
            continue
        friendly_name = agent_map.get(agent_name, agent_name)
        if friendly_name not in seen:
            seen.add(friendly_name)
            # Combine both debate agents into one "Debate" entry
            if friendly_name == "Debate":
                if "Debate" not in path_parts:
                    path_parts.append(friendly_name)
            else:
                path_parts.append(friendly_name)
    
    return " → ".join(path_parts)


def generate_customer_explanation_llm(state: GraphState, llm: LLMService) -> str:
    """Generate customer-facing explanation using LLM with YAML prompts."""
    decision = state["decision"]
    consolidated = state["consolidated"]
    
    system_prompt, user_prompt = get_customer_explanation_prompts(
        amount=consolidated.get("amount", "N/A"),
        decision=decision,
    )

    return llm.generate(user_prompt, system_prompt=system_prompt, max_tokens=150)


def generate_audit_explanation_llm(state: GraphState, llm: LLMService) -> str:
    """Generate audit-facing explanation using LLM with YAML prompts."""
    transaction_id = state["transaction_id"]
    decision = state["decision"]
    signals = state["signals"]
    confidence = state["confidence"]
    citations_internal = state["citations_internal"]
    citations_external = state["citations_external"]
    debate = state["debate"]
    
    system_prompt, user_prompt = get_audit_explanation_prompts(
        transaction_id=transaction_id,
        decision=decision,
        confidence=confidence,
        signals=", ".join(signals) if signals else "Ninguna",
        internal_citations=len(citations_internal),
        external_citations=len(citations_external),
        pro_fraud_reasoning=debate.get("pro_fraud", {}).get("reasoning", "N/A"),
        pro_customer_reasoning=debate.get("pro_customer", {}).get("reasoning", "N/A"),
    )

    return llm.generate(user_prompt, system_prompt=system_prompt, max_tokens=1500)


def run_explainability_agent_mock(state: GraphState, audit_repo=None) -> tuple[str, str, str]:
    """Mock explainability logic (rule-based) with hybrid template."""
    decision = state["decision"]
    signals = state["signals"]
    citations_internal = state["citations_internal"]
    citations_external = state["citations_external"]
    confidence = state["confidence"]
    transaction_id = state["transaction_id"]
    metrics = state.get("metrics", {})
    debate = state.get("debate", {})
    hitl = state.get("hitl", {})
    
    # Decision labels in Spanish
    decision_labels = {
        "APPROVE": "Aprobada",
        "CHALLENGE": "Requiere validación",
        "BLOCK": "Bloqueada",
        "ESCALATE_TO_HUMAN": "Revisión humana"
    }
    
    # Customer explanation based on decision
    if decision == "APPROVE":
        explanation_customer = "La transacción fue aprobada. No se detectaron señales relevantes."
    elif decision == "CHALLENGE":
        explanation_customer = "La transacción requiere validación adicional por señales inusuales detectadas."
    elif decision == "BLOCK":
        explanation_customer = "La transacción fue bloqueada por alta probabilidad de fraude según señales y evidencias."
    else:  # ESCALATE_TO_HUMAN
        explanation_customer = "La transacción requiere revisión humana para una validación adicional."
    
    # Build dynamic agent path
    if audit_repo:
        agent_path = build_agent_path(transaction_id, audit_repo)
    else:
        agent_path = "Context → Behavior → RAG → Web → Debate → Arbiter → Explainability"
    
    # Short audit explanation
    audit_parts = []
    if citations_internal:
        policy_ids = [c["policy_id"] for c in citations_internal]
        audit_parts.append(f"Se aplicó la política {', '.join(policy_ids)}")
    if citations_external:
        audit_parts.append(f"se detectó alerta externa")
    audit_parts.append(f"Ruta de agentes: {agent_path}")
    explanation_audit = ". ".join(audit_parts) + "."
    
    # Hybrid AI summary template
    summary_parts = []
    # summary_parts.append(f"**Informe Detallado de IA – Transacción {transaction_id}**\\n\\n")
    
    # 1) Decisión final y nivel de confianza
    summary_parts.append("## 1) Decisión final y nivel de confianza\\n\\n")
    summary_parts.append(f"**Decisión:** {decision_labels.get(decision, decision)} ({decision})\\n\\n")
    summary_parts.append(f"**Riesgo de fraude:** {int(confidence * 100)}% ({confidence:.2f})\\n\\n")
    
    # Generate one-line reason based on signals and decision
    if signals:
        if len(signals) > 1:
            reason = f"{signals[0]} y {len(signals)-1} señal{'es' if len(signals) > 2 else ''} adicional{'es' if len(signals) > 2 else ''} detectadas."
        else:
            reason = signals[0]
    elif decision == "APPROVE":
        reason = "Transacción dentro de parámetros normales del cliente."
    else:
        reason = "Requiere evaluación adicional por contexto de riesgo."
    
    summary_parts.append(f"**Resumen:** {reason}\\n\\n")
    
    # 2) Señales clave
    summary_parts.append("## 2) Señales clave que influyeron en la decisión\\n\\n")
    if signals:
        for signal in signals:
            # Add metric context if available
            metric_detail = ""
            if "behavior_risk" in metrics:
                metric_detail = f" (riesgo comportamental: {metrics['behavior_risk']:.2f})"
            elif "amount_ratio" in metrics:
                metric_detail = f" (ratio: {metrics['amount_ratio']:.2f}x)"
            summary_parts.append(f"- {signal}{metric_detail}\\n")
    else:
        summary_parts.append("- No se detectaron señales de riesgo significativas.\\n")
    summary_parts.append("\\n")
    
    # 3) Políticas internas aplicadas
    summary_parts.append("## 3) Políticas internas aplicadas (RAG)\\n\\n")
    if citations_internal:
        for idx, cit in enumerate(citations_internal, 1):
            policy_id = cit.get("policy_id", "N/A")
            version = cit.get("version", "N/A")
            chunk_id = cit.get("chunk_id", "N/A")
            summary_parts.append(f"**Política {idx}:** {policy_id} versión {version} (fragmento {chunk_id})\\n\\n")
        
        # Generate application explanation
        summary_parts.append("**Aplicación:** ")
        if decision == "CHALLENGE":
            summary_parts.append("Las políticas detectadas establecen umbrales de validación que aplican a esta transacción. Se requiere verificación adicional del cliente antes de aprobar.\\n")
        elif decision == "BLOCK":
            summary_parts.append("Las condiciones definidas en las políticas justifican el bloqueo inmediato por alto riesgo de fraude.\\n")
        elif decision == "ESCALATE_TO_HUMAN":
            summary_parts.append("Las políticas requieren escalamiento a revisión humana para casos con estas características específicas.\\n")
        else:
            summary_parts.append("Las políticas validan que la transacción cumple con los criterios de aprobación establecidos.\\n")
    else:
        summary_parts.append("Sin políticas recuperadas.\\n")
    summary_parts.append("\\n")
    
    # 4) Inteligencia de amenazas externas
    summary_parts.append("## 4) Inteligencia de amenazas externas (búsqueda gobernada)\\n\\n")
    summary_parts.append(f"**Resultados:** {len(citations_external)}\\n\\n")
    if citations_external:
        for cit in citations_external:
            url = cit.get("url", "N/A")
            summary_text = cit.get("summary", "Sin resumen")
            summary_parts.append(f"- {url} — {summary_text}\\n")
    else:
        summary_parts.append("No se registraron alertas externas relevantes en las fuentes permitidas.\\n")
    summary_parts.append("\\n")
    
    # 5) Resumen del debate
    summary_parts.append("## 5) Resumen del debate entre agentes Pro-Fraude y Pro-Cliente\\n\\n")
    
    # Anchor debate to signals/evidence
    pro_fraud_reasoning = debate.get("pro_fraud", {}).get("reasoning", "")
    pro_customer_reasoning = debate.get("pro_customer", {}).get("reasoning", "")
    
    if pro_fraud_reasoning:
        summary_parts.append(f"**Pro-Fraude:** {pro_fraud_reasoning[:150]}{'...' if len(pro_fraud_reasoning) > 150 else ''}\\n\\n")
    else:
        summary_parts.append(f"**Pro-Fraude:** Las señales detectadas sugieren un nivel de riesgo que justifica precaución.\\n\\n")
    
    if pro_customer_reasoning:
        summary_parts.append(f"**Pro-Cliente:** {pro_customer_reasoning[:150]}{'...' if len(pro_customer_reasoning) > 150 else ''}\\n\\n")
    else:
        summary_parts.append(f"**Pro-Cliente:** Algunos patrones del cliente coinciden con su comportamiento habitual.\\n\\n")
    
    # 6) Trazabilidad y siguientes pasos
    summary_parts.append("## 6) Trazabilidad y siguientes pasos\\n\\n")
    summary_parts.append(f"**Ruta de agentes:** {agent_path}\\n\\n")
    
    hitl_required = hitl.get("required", False)
    hitl_reason = hitl.get("reason", "N/A")
    summary_parts.append(f"**¿Se necesita intervención humana?:** {'Sí' if hitl_required else 'No'}")
    if hitl_required:
        summary_parts.append(f" — {hitl_reason}")
    summary_parts.append("\\n\\n")
    
    # Recommended action aligned with decision
    summary_parts.append("**Acción recomendada:** ")
    if decision == "APPROVE":
        summary_parts.append("Procesar la transacción normalmente. El riesgo es aceptable dentro de los parámetros establecidos.")
    elif decision == "CHALLENGE":
        summary_parts.append("Solicitar validación adicional del cliente (OTP, biometría, etc.) antes de aprobar.")
    elif decision == "BLOCK":
        summary_parts.append("Bloquear la transacción y notificar al cliente sobre actividad sospechosa detectada.")
    else:  # ESCALATE_TO_HUMAN
        summary_parts.append("Derivar el caso a un analista especializado para revisión manual y decisión final.")
    summary_parts.append("\\n")
    
    ai_summary = "".join(summary_parts)
    
    return explanation_customer, explanation_audit, ai_summary


def run_explainability_agent(state: GraphState, llm: LLMService | None = None, audit_repo=None) -> GraphState:
    """
    Explainability Agent: Generates explanations for customer, audit, and detailed AI summary.
    
    Uses LLM if provided, otherwise falls back to mock logic.
    
    Generates three outputs:
    - explanation_customer: Friendly, non-technical for customers
    - explanation_audit: Short technical summary (policy, action, agent path)
    - ai_summary: Strict template-based detailed report
    """
    # Build dynamic agent path
    transaction_id = state["transaction_id"]
    if audit_repo:
        agent_path = build_agent_path(transaction_id, audit_repo)
    else:
        agent_path = "Context → Behavior → RAG → Web → Debate → Arbiter → Explainability"
    
    if llm:
        # Generate customer explanation with LLM
        explanation_customer = generate_customer_explanation_llm(state, llm)
        
        # Generate AI summary with LLM (will follow strict template from prompt)
        ai_summary = generate_audit_explanation_llm(state, llm)
        
        # Generate short audit summary with dynamic path
        decision = state["decision"]
        citations_internal = state["citations_internal"]
        citations_external = state["citations_external"]
        
        audit_parts = []
        if citations_internal:
            policy_ids = [c["policy_id"] for c in citations_internal]
            audit_parts.append(f"Se aplicó la política {', '.join(policy_ids)}")
        if citations_external:
            audit_parts.append("se detectó alerta externa")
        audit_parts.append(f"Ruta de agentes: {agent_path}")
        
        explanation_audit = ". ".join(audit_parts) + "."
    else:
        # Use mock with strict template
        explanation_customer, explanation_audit, ai_summary = run_explainability_agent_mock(state, audit_repo)
    
    log_agent_event(
        agent="Explainability",
        message=f"Generated explanations for {state['decision']}",
        transaction_id=state["transaction_id"]
    )
    
    return {
        **state,
        "explanation_customer": explanation_customer,
        "explanation_audit": explanation_audit,
        "ai_summary": ai_summary,
    }
