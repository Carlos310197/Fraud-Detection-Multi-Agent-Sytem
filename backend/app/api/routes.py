"""FastAPI routes for the fraud detection API."""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends

from app.api.schemas import (
    IngestResponse,
    AnalyzeAllResponse,
    DecisionResponse,
    TransactionSummary,
    TransactionDetailResponse,
    HitlCase,
    HitlResolution,
    AuditEvent,
    ErrorResponse,
    Transaction,
    CustomerBehavior,
)
from app.core.config import get_settings, Settings
from app.core.errors import TransactionNotFoundError, HITLCaseNotFoundError
from app.core.logging import logger
from app.data.loader import (
    load_transactions,
    load_customer_behavior,
    load_policies,
    consolidate,
)
from app.storage.local_json import (
    LocalJSONTransactionRepository,
    LocalJSONAuditRepository,
    LocalJSONHitlRepository,
)
from app.rag.embedder import get_embedder
from app.rag.vector_store import VectorStore
from app.rag.index_policies import index_policies
from app.web.allowlist import Allowlist
from app.web.governed_search import GovernedSearchService, get_search_provider
from app.orchestration.graph import AgentDependencies, run_fraud_detection
from app.core.llm import get_llm_service


router = APIRouter()


# Global state for loaded data (in production, use proper dependency injection)
_transactions: dict[str, Transaction] = {}
_customers: dict[str, CustomerBehavior] = {}


def get_dependencies(settings: Settings = Depends(get_settings)) -> AgentDependencies:
    """Create agent dependencies from settings."""
    # Embedder
    embedder = get_embedder(settings.EMBEDDINGS_PROVIDER, settings=settings)
    
    # Vector store
    vector_store = VectorStore(
        persist_directory=settings.VECTOR_DIR,
        collection_name="fraud_policies",
        embedder=embedder,
    )
    
    # Allowlist and search
    allowlist = Allowlist(settings.allowlist_domains)
    search_provider = get_search_provider(settings.WEB_SEARCH_PROVIDER, allowlist)
    search_service = GovernedSearchService(search_provider, settings.WEB_MAX_RESULTS)
    
    # Repositories
    transaction_repo = LocalJSONTransactionRepository(settings.STORE_DIR)
    audit_repo = LocalJSONAuditRepository(settings.STORE_DIR)
    hitl_repo = LocalJSONHitlRepository(settings.STORE_DIR)
    
    # LLM Service (optional)
    llm_service = get_llm_service(settings)
    
    return AgentDependencies(
        vector_store=vector_store,
        search_service=search_service,
        audit_repo=audit_repo,
        hitl_repo=hitl_repo,
        llm_service=llm_service,
    )


def get_transaction_repo(settings: Settings = Depends(get_settings)) -> LocalJSONTransactionRepository:
    """Get transaction repository."""
    return LocalJSONTransactionRepository(settings.STORE_DIR)


def get_audit_repo(settings: Settings = Depends(get_settings)) -> LocalJSONAuditRepository:
    """Get audit repository."""
    return LocalJSONAuditRepository(settings.STORE_DIR)


def get_hitl_repo(settings: Settings = Depends(get_settings)) -> LocalJSONHitlRepository:
    """Get HITL repository."""
    return LocalJSONHitlRepository(settings.STORE_DIR)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_data(settings: Settings = Depends(get_settings)):
    """
    Load data from files and prepare the system for analysis.
    
    - Loads transactions from CSV
    - Loads customer behavior from CSV
    - Loads and indexes fraud policies
    """
    global _transactions, _customers
    
    data_dir = Path(settings.DATA_DIR)
    
    try:
        # Load transactions
        transactions = load_transactions(data_dir / "transactions.csv")
        _transactions = transactions
        
        # Load customer behavior
        customers = load_customer_behavior(data_dir / "customer_behavior.csv")
        _customers = customers
        
        # Load policies
        policies = load_policies(data_dir / "fraud_policies.json")
        
        # Initialize repositories and save data
        txn_repo = LocalJSONTransactionRepository(settings.STORE_DIR)
        
        for txn in transactions.values():
            txn_repo.save_transaction(txn)
        
        for customer in customers.values():
            txn_repo.save_customer_behavior(customer)
        
        # Index policies in vector store
        embedder = get_embedder(settings.EMBEDDINGS_PROVIDER, settings=settings)
        vector_store = VectorStore(
            persist_directory=settings.VECTOR_DIR,
            collection_name="fraud_policies",
            embedder=embedder,
        )
        
        # Clear and re-index
        vector_store.clear()
        index_policies(policies, vector_store)
        
        logger.info(f"Ingested {len(transactions)} transactions, {len(customers)} customers, {len(policies)} policies")
        
        return IngestResponse(
            transactions_loaded=len(transactions),
            customers_loaded=len(customers),
            policies_loaded=len(policies),
        )
    
    except Exception as e:
        logger.error(f"Ingest failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transactions/{transaction_id}/analyze", response_model=DecisionResponse)
async def analyze_transaction(
    transaction_id: str,
    settings: Settings = Depends(get_settings),
):
    """
    Analyze a transaction and return a fraud decision.
    
    Runs the full multi-agent pipeline and persists the decision.
    """
    global _transactions, _customers
    
    # Reload data if not loaded
    if not _transactions:
        data_dir = Path(settings.DATA_DIR)
        _transactions = load_transactions(data_dir / "transactions.csv")
        _customers = load_customer_behavior(data_dir / "customer_behavior.csv")
    
    # Validate transaction exists
    if transaction_id not in _transactions:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    
    try:
        # Consolidate data
        consolidated = consolidate(transaction_id, _transactions, _customers)
        
        # Get dependencies
        deps = get_dependencies(settings)
        
        # Run fraud detection
        decision = run_fraud_detection(
            transaction_id=transaction_id,
            consolidated_data=consolidated.model_dump(),
            deps=deps,
        )
        
        # Persist decision
        txn_repo = LocalJSONTransactionRepository(settings.STORE_DIR)
        txn_repo.save_decision(transaction_id, decision)
        
        return decision
    
    except TransactionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed for {transaction_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transactions/analyze-all", response_model=AnalyzeAllResponse)
async def analyze_all_pending(
    settings: Settings = Depends(get_settings),
):
    """
    Analyze all transactions that don't have a decision yet.
    
    Returns the number of transactions analyzed and their results.
    """
    global _transactions, _customers
    
    # Reload data if not loaded
    if not _transactions:
        data_dir = Path(settings.DATA_DIR)
        _transactions = load_transactions(data_dir / "transactions.csv")
        _customers = load_customer_behavior(data_dir / "customer_behavior.csv")
    
    txn_repo = LocalJSONTransactionRepository(settings.STORE_DIR)
    deps = get_dependencies(settings)
    
    # Find transactions without decisions
    pending_transactions = []
    for txn_id in _transactions.keys():
        existing_decision = txn_repo.get_decision(txn_id)
        if not existing_decision:
            pending_transactions.append(txn_id)
    
    if not pending_transactions:
        return AnalyzeAllResponse(analyzed=0, results=[])
    
    logger.info(f"Starting bulk analysis of {len(pending_transactions)} pending transactions")
    
    results = []
    analyzed_count = 0
    
    for txn_id in pending_transactions:
        try:
            # Consolidate data
            consolidated = consolidate(txn_id, _transactions, _customers)
            
            # Run fraud detection
            decision = run_fraud_detection(
                transaction_id=txn_id,
                consolidated_data=consolidated.model_dump(),
                deps=deps,
            )
            
            # Persist decision
            txn_repo.save_decision(txn_id, decision)
            
            results.append(decision)
            analyzed_count += 1
            
            logger.info(f"Analyzed {txn_id}: {decision.decision} (confidence: {decision.confidence})")
            
        except Exception as e:
            logger.error(f"Failed to analyze {txn_id}: {e}", exc_info=True)
            # Continue with next transaction instead of failing the entire batch
            continue
    
    logger.info(f"Bulk analysis completed: {analyzed_count}/{len(pending_transactions)} successful")
    
    return AnalyzeAllResponse(
        analyzed=analyzed_count,
        results=results
    )


@router.get("/transactions", response_model=list[TransactionSummary])
async def list_transactions(
    txn_repo: LocalJSONTransactionRepository = Depends(get_transaction_repo),
):
    """List all transactions with their latest decisions."""
    return txn_repo.list_transactions()


@router.get("/transactions/{transaction_id}", response_model=TransactionDetailResponse)
async def get_transaction_detail(
    transaction_id: str,
    txn_repo: LocalJSONTransactionRepository = Depends(get_transaction_repo),
    audit_repo: LocalJSONAuditRepository = Depends(get_audit_repo),
):
    """Get full transaction details including audit trail."""
    transaction = txn_repo.get_transaction(transaction_id)
    
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    
    customer_behavior = txn_repo.get_customer_behavior(transaction.customer_id)
    latest_decision = txn_repo.get_decision(transaction_id)
    audit_events = audit_repo.get_events(transaction_id)
    
    return TransactionDetailResponse(
        transaction=transaction,
        customer_behavior=customer_behavior,
        latest_decision=latest_decision,
        audit_events=audit_events,
    )


@router.get("/hitl", response_model=list[HitlCase])
async def list_hitl_cases(
    hitl_repo: LocalJSONHitlRepository = Depends(get_hitl_repo),
):
    """List all open HITL cases."""
    return hitl_repo.list_open_cases()


@router.post("/hitl/{case_id}/resolve", response_model=HitlCase)
async def resolve_hitl_case(
    case_id: str,
    resolution: HitlResolution,
    settings: Settings = Depends(get_settings),
):
    """Resolve a HITL case with a decision."""
    hitl_repo = LocalJSONHitlRepository(settings.STORE_DIR)
    audit_repo = LocalJSONAuditRepository(settings.STORE_DIR)
    txn_repo = LocalJSONTransactionRepository(settings.STORE_DIR)
    
    case = hitl_repo.get_case(case_id)
    
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    
    if case.status == "RESOLVED":
        raise HTTPException(status_code=400, detail="Case already resolved")
    
    resolved_at = datetime.now(timezone.utc).isoformat()
    
    # Resolve the case
    hitl_repo.resolve_case(
        case_id=case_id,
        resolution={
            "decision": resolution.decision,
            "notes": resolution.notes,
        },
        resolved_at=resolved_at,
    )
    
    # Record audit event
    seq = audit_repo.get_next_seq(case.transaction_id)
    audit_event = AuditEvent(
        transaction_id=case.transaction_id,
        run_id="hitl-manual",  # Manual HITL resolution
        seq=seq,
        ts=resolved_at,
        duration_ms=0.0,  # Manual action, no duration
        agent="HITL",
        input_summary=f"case_id={case_id}, original_reason={case.reason}",
        output_summary=f"decision={resolution.decision}",
        output_json={
            "decision": resolution.decision,
            "notes": resolution.notes,
        },
    )
    audit_repo.append_event(audit_event)
    
    # Update transaction decision
    original_decision = txn_repo.get_decision(case.transaction_id)
    if original_decision:
        updated_decision = DecisionResponse(
            decision=resolution.decision,
            confidence=original_decision.confidence,
            signals=original_decision.signals,
            citations_internal=original_decision.citations_internal,
            citations_external=original_decision.citations_external,
            explanation_customer=f"Resolución manual: {resolution.notes}",
            explanation_audit=f"{original_decision.explanation_audit} Resolución HITL: {resolution.decision} - {resolution.notes}",
            ai_summary=original_decision.ai_summary,
            hitl=original_decision.hitl,
        )
        txn_repo.save_decision(case.transaction_id, updated_decision)
    
    # Return updated case
    return hitl_repo.get_case(case_id)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
