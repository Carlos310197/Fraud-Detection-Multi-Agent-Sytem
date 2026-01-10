"""LangGraph orchestration for multi-agent fraud detection."""
from datetime import datetime, timezone
from typing import Any, Callable
import uuid
import time

from langgraph.graph import StateGraph, END

from app.orchestration.state import GraphState, create_initial_state
from app.agents.transaction_context import run_transaction_context_agent
from app.agents.behavioral_pattern import run_behavioral_pattern_agent
from app.agents.policy_rag import run_policy_rag_agent
from app.agents.threat_intel import run_threat_intel_agent
from app.agents.evidence_aggregation import run_evidence_aggregation_agent
from app.agents.debate import run_debate_pro_fraud_agent, run_debate_pro_customer_agent
from app.agents.arbiter import run_arbiter_agent
from app.agents.explainability import run_explainability_agent
from app.api.schemas import AuditEvent, HitlCase, DecisionResponse, CitationInternal, CitationExternal, HitlInfo
from app.storage.interfaces import AuditRepository, HitlRepository
from app.rag.vector_store import VectorStore
from app.web.governed_search import GovernedSearchService
from app.core.logging import logger
from app.core.errors import AgentExecutionError
from app.core.llm import LLMService


class AgentDependencies:
    """Container for agent dependencies."""
    
    def __init__(
        self,
        vector_store: VectorStore,
        search_service: GovernedSearchService,
        audit_repo: AuditRepository,
        hitl_repo: HitlRepository,
        llm_service: LLMService | None = None,
        run_id: str | None = None,
    ):
        self.vector_store = vector_store
        self.search_service = search_service
        self.audit_repo = audit_repo
        self.hitl_repo = hitl_repo
        self.llm_service = llm_service
        self.run_id = run_id or str(uuid.uuid4())


def create_audit_event(
    transaction_id: str,
    run_id: str,
    seq: int,
    agent: str,
    input_summary: str,
    output_summary: str,
    output_json: dict[str, Any],
    duration_ms: float,
) -> AuditEvent:
    """Create an audit event with current timestamp."""
    return AuditEvent(
        transaction_id=transaction_id,
        run_id=run_id,
        seq=seq,
        ts=datetime.now(timezone.utc).isoformat(),
        duration_ms=duration_ms,
        agent=agent,
        input_summary=input_summary,
        output_summary=output_summary,
        output_json=output_json,
    )


def wrap_agent_node(
    agent_name: str,
    agent_fn: Callable[[GraphState], GraphState],
    deps: AgentDependencies,
) -> Callable[[GraphState], GraphState]:
    """
    Wrap an agent function with audit trail recording.
    
    Responsibilities:
    - Construct input_summary
    - Execute agent function
    - Construct output_summary
    - Record audit event
    - Handle exceptions (escalate to human on error)
    """
    def wrapped(state: GraphState) -> GraphState:
        transaction_id = state["transaction_id"]
        seq = deps.audit_repo.get_next_seq(transaction_id)
        
        # Build input summary
        input_summary = f"signals={len(state['signals'])}, metrics_keys={list(state['metrics'].keys())}"
        
        # Track execution time
        start_time = time.time()
        
        try:
            # Execute agent
            new_state = agent_fn(state)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Build output summary
            output_summary = f"signals={len(new_state['signals'])}"
            if new_state.get("decision"):
                output_summary += f", decision={new_state['decision']}"
            if new_state.get("confidence") is not None:
                output_summary += f", confidence={new_state['confidence']}"
            
            # Create and store audit event
            event = create_audit_event(
                transaction_id=transaction_id,
                run_id=deps.run_id,
                seq=seq,
                agent=agent_name,
                input_summary=input_summary,
                output_summary=output_summary,
                output_json={
                    "signals": new_state["signals"],
                    "metrics": new_state["metrics"],
                    "decision": new_state.get("decision"),
                    "confidence": new_state.get("confidence"),
                },
                duration_ms=duration_ms,
            )
            deps.audit_repo.append_event(event)
            
            return new_state
            
        except Exception as e:
            # Log error
            logger.error(f"Agent {agent_name} failed: {e}", exc_info=True)
            
            # Calculate duration even for errors
            duration_ms = (time.time() - start_time) * 1000
            
            # Record error event
            error_event = create_audit_event(
                transaction_id=transaction_id,
                run_id=deps.run_id,
                seq=seq,
                agent=f"{agent_name}_error",
                input_summary=input_summary,
                output_summary=f"Error: {str(e)}",
                output_json={"error": str(e)},
                duration_ms=duration_ms,
            )
            deps.audit_repo.append_event(error_event)
            
            # Force escalation
            return {
                **state,
                "decision": "ESCALATE_TO_HUMAN",
                "hitl": {
                    "required": True,
                    "reason": f"agent_error:{agent_name}",
                },
            }
    
    return wrapped


def wrap_agent_with_deps(
    agent_name: str,
    agent_fn: Callable,
    deps: AgentDependencies,
    pass_vector_store: bool = False,
    pass_search_service: bool = False,
    pass_llm: bool = False,
    pass_audit_repo: bool = False,
) -> Callable[[GraphState], GraphState]:
    """
    Wrap an agent that needs dependencies.
    """
    def wrapped(state: GraphState) -> GraphState:
        transaction_id = state["transaction_id"]
        seq = deps.audit_repo.get_next_seq(transaction_id)
        
        input_summary = f"signals={len(state['signals'])}, metrics_keys={list(state['metrics'].keys())}"
        
        # Track execution time
        start_time = time.time()
        
        try:
            # Execute agent with appropriate dependencies
            if pass_vector_store:
                new_state = agent_fn(state, deps.vector_store)
            elif pass_search_service:
                new_state = agent_fn(state, deps.search_service)
            elif pass_llm and pass_audit_repo:
                new_state = agent_fn(state, deps.llm_service, deps.audit_repo)
            elif pass_llm:
                new_state = agent_fn(state, deps.llm_service)
            elif pass_audit_repo:
                new_state = agent_fn(state, audit_repo=deps.audit_repo)
            else:
                new_state = agent_fn(state)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Build output summary
            output_summary = f"signals={len(new_state['signals'])}"
            if agent_name == "PolicyRAG":
                output_summary += f", citations={len(new_state['citations_internal'])}"
            if agent_name == "ThreatIntel":
                output_summary += f", external_citations={len(new_state['citations_external'])}"
            if new_state.get("decision"):
                output_summary += f", decision={new_state['decision']}"
            
            # Create and store audit event
            event = create_audit_event(
                transaction_id=transaction_id,
                run_id=deps.run_id,
                seq=seq,
                agent=agent_name,
                input_summary=input_summary,
                output_summary=output_summary,
                output_json={
                    "signals": new_state["signals"],
                    "metrics": new_state["metrics"],
                    "citations_internal": new_state.get("citations_internal", []),
                    "citations_external": new_state.get("citations_external", []),
                    "decision": new_state.get("decision"),
                },
                duration_ms=duration_ms,
            )
            deps.audit_repo.append_event(event)
            
            return new_state
            
        except Exception as e:
            logger.error(f"Agent {agent_name} failed: {e}", exc_info=True)
            
            # Calculate duration even for errors
            duration_ms = (time.time() - start_time) * 1000
            
            error_event = create_audit_event(
                transaction_id=transaction_id,
                run_id=deps.run_id,
                seq=seq,
                agent=f"{agent_name}_error",
                input_summary=input_summary,
                output_summary=f"Error: {str(e)}",
                output_json={"error": str(e)},
                duration_ms=duration_ms,
            )
            deps.audit_repo.append_event(error_event)
            
            return {
                **state,
                "decision": "ESCALATE_TO_HUMAN",
                "hitl": {
                    "required": True,
                    "reason": f"agent_error:{agent_name}",
                },
            }
    
    return wrapped


def create_hitl_gate(deps: AgentDependencies) -> Callable[[GraphState], GraphState]:
    """Create the HITL gate node that creates cases when needed."""
    
    def hitl_gate(state: GraphState) -> GraphState:
        if state["hitl"]["required"]:
            # Check if case already exists
            existing = deps.hitl_repo.get_case_by_transaction(state["transaction_id"])
            
            if not existing:
                # Create new HITL case
                case = HitlCase(
                    case_id=f"HITL-{uuid.uuid4().hex[:8].upper()}",
                    transaction_id=state["transaction_id"],
                    status="OPEN",
                    reason=state["hitl"]["reason"],
                    created_at=datetime.now(timezone.utc).isoformat(),
                    resolved_at=None,
                    resolution=None,
                )
                deps.hitl_repo.create_case(case)
                
                logger.info(f"Created HITL case {case.case_id} for {state['transaction_id']}")
        
        return state
    
    return hitl_gate


def build_fraud_detection_graph(deps: AgentDependencies) -> StateGraph:
    """
    Build the LangGraph state graph for fraud detection.
    
    Node order:
    1) Context
    2) Behavior
    3) PolicyRAG
    4) ThreatIntel
    5) EvidenceAggregation
    6) DebateProFraud
    7) DebateProCustomer
    8) Arbiter
    9) Explainability
    10) HITLGate
    """
    # Create the graph
    graph = StateGraph(GraphState)
    
    # Add nodes with audit wrappers
    graph.add_node(
        "context",
        wrap_agent_node("TransactionContext", run_transaction_context_agent, deps)
    )
    
    graph.add_node(
        "behavior",
        wrap_agent_node("BehavioralPattern", run_behavioral_pattern_agent, deps)
    )
    
    graph.add_node(
        "policy_rag",
        wrap_agent_with_deps("PolicyRAG", run_policy_rag_agent, deps, pass_vector_store=True)
    )
    
    graph.add_node(
        "threat_intel",
        wrap_agent_with_deps("ThreatIntel", run_threat_intel_agent, deps, pass_search_service=True)
    )
    
    graph.add_node(
        "evidence_aggregation",
        wrap_agent_node("EvidenceAggregation", run_evidence_aggregation_agent, deps)
    )
    
    graph.add_node(
        "debate_fraud",
        wrap_agent_with_deps("DebateProFraud", run_debate_pro_fraud_agent, deps, pass_llm=True)
    )
    
    graph.add_node(
        "debate_customer",
        wrap_agent_with_deps("DebateProCustomer", run_debate_pro_customer_agent, deps, pass_llm=True)
    )
    
    graph.add_node(
        "arbiter",
        wrap_agent_node("Arbiter", run_arbiter_agent, deps)
    )
    
    graph.add_node(
        "explainability",
        wrap_agent_with_deps("Explainability", run_explainability_agent, deps, pass_llm=True, pass_audit_repo=True)
    )
    
    graph.add_node(
        "hitl_gate",
        create_hitl_gate(deps)
    )
    
    # Set entry point
    graph.set_entry_point("context")
    
    # Add edges (linear flow)
    graph.add_edge("context", "behavior")
    graph.add_edge("behavior", "policy_rag")
    graph.add_edge("policy_rag", "threat_intel")
    graph.add_edge("threat_intel", "evidence_aggregation")
    graph.add_edge("evidence_aggregation", "debate_fraud")
    graph.add_edge("debate_fraud", "debate_customer")
    graph.add_edge("debate_customer", "arbiter")
    graph.add_edge("arbiter", "explainability")
    graph.add_edge("explainability", "hitl_gate")
    graph.add_edge("hitl_gate", END)
    
    return graph


def run_fraud_detection(
    transaction_id: str,
    consolidated_data: dict[str, Any],
    deps: AgentDependencies,
) -> DecisionResponse:
    """
    Run the full fraud detection pipeline for a transaction.
    
    Args:
        transaction_id: The transaction ID
        consolidated_data: Consolidated transaction + customer data as dict
        deps: Agent dependencies
        
    Returns:
        DecisionResponse with the final decision
    """
    # Create initial state
    initial_state = create_initial_state(transaction_id, consolidated_data)
    
    # Build and compile graph
    graph = build_fraud_detection_graph(deps)
    app = graph.compile()
    
    # Run the graph
    final_state = app.invoke(initial_state)
    
    # Build response
    return DecisionResponse(
        decision=final_state["decision"],
        confidence=final_state["confidence"],
        signals=final_state["signals"],
        citations_internal=[
            CitationInternal(**c) for c in final_state["citations_internal"]
        ],
        citations_external=[
            CitationExternal(**c) for c in final_state["citations_external"]
        ],
        explanation_customer=final_state["explanation_customer"],
        explanation_audit=final_state["explanation_audit"],
        ai_summary=final_state["ai_summary"],
        hitl=HitlInfo(**final_state["hitl"]),
    )
