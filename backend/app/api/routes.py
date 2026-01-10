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
from app.data.s3_loader import (
    load_transactions_from_s3,
    load_customer_behavior_from_s3,
    load_policies_from_s3,
)
from app.storage.interfaces import TransactionRepository, AuditRepository, HitlRepository
from app.storage.local_json import (
    LocalJSONTransactionRepository,
    LocalJSONAuditRepository,
    LocalJSONHitlRepository,
)
from app.storage.dynamodb import (
    DynamoDBTransactionRepository,
    DynamoDBAuditRepository,
    DynamoDBHitlRepository,
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


def _build_repositories(settings: Settings) -> tuple[TransactionRepository, AuditRepository, HitlRepository]:
    if settings.STORAGE_BACKEND == "dynamodb":
        transaction_repo = DynamoDBTransactionRepository(
            settings.DDB_TABLE_TRANSACTIONS,
            region=settings.AWS_REGION,
        )
        audit_repo = DynamoDBAuditRepository(
            settings.DDB_TABLE_AUDIT,
            region=settings.AWS_REGION,
        )
        hitl_repo = DynamoDBHitlRepository(
            settings.DDB_TABLE_HITL,
            region=settings.AWS_REGION,
        )
        return transaction_repo, audit_repo, hitl_repo

    transaction_repo = LocalJSONTransactionRepository(settings.STORE_DIR)
    audit_repo = LocalJSONAuditRepository(settings.STORE_DIR)
    hitl_repo = LocalJSONHitlRepository(settings.STORE_DIR)
    return transaction_repo, audit_repo, hitl_repo


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
    _, audit_repo, hitl_repo = _build_repositories(settings)
    
    # LLM Service (optional)
    llm_service = get_llm_service(settings)
    
    return AgentDependencies(
        vector_store=vector_store,
        search_service=search_service,
        audit_repo=audit_repo,
        hitl_repo=hitl_repo,
        llm_service=llm_service,
    )


def get_transaction_repo(settings: Settings = Depends(get_settings)) -> TransactionRepository:
    """Get transaction repository."""
    transaction_repo, _, _ = _build_repositories(settings)
    return transaction_repo


def get_audit_repo(settings: Settings = Depends(get_settings)) -> AuditRepository:
    """Get audit repository."""
    _, audit_repo, _ = _build_repositories(settings)
    return audit_repo


def get_hitl_repo(settings: Settings = Depends(get_settings)) -> HitlRepository:
    """Get HITL repository."""
    _, _, hitl_repo = _build_repositories(settings)
    return hitl_repo


@router.post("/ingest", response_model=IngestResponse)
async def ingest_data(settings: Settings = Depends(get_settings)):
    """
    Load data from files and prepare the system for analysis.
    
    - Loads transactions from CSV
    - Loads customer behavior from CSV
    - Loads and indexes fraud policies
    
    In AWS mode, reads from S3 bucket (INPUT_BUCKET env var).
    In local mode, reads from DATA_DIR filesystem.
    """
    global _transactions, _customers
    
    try:
        # Check if running in AWS mode with S3
        if settings.APP_ENV == "aws" and hasattr(settings, "INPUT_BUCKET"):
            bucket = settings.INPUT_BUCKET
            logger.info(f"Loading data from S3 bucket: {bucket}")
            
            # Load from S3
            transactions = load_transactions_from_s3(bucket, "transactions.csv")
            _transactions = transactions
            
            customers = load_customer_behavior_from_s3(bucket, "customer_behavior.csv")
            _customers = customers
            
            policies = load_policies_from_s3(bucket, "fraud_policies.json")
        else:
            # Load from local filesystem
            data_dir = Path(settings.DATA_DIR)
            logger.info(f"Loading data from local directory: {data_dir}")
            
            transactions = load_transactions(data_dir / "transactions.csv")
            _transactions = transactions
            
            customers = load_customer_behavior(data_dir / "customer_behavior.csv")
            _customers = customers
            
            policies = load_policies(data_dir / "fraud_policies.json")
        
        # Initialize repositories and save data
        txn_repo, _, _ = _build_repositories(settings)
        
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
    # In DynamoDB mode, fetch per-request to avoid relying on local CSVs or global cache
    if settings.STORAGE_BACKEND == "dynamodb":
        logger.info(f"Analyze request for {transaction_id} using DynamoDB backend")
        txn_repo, _, _ = _build_repositories(settings)
        txn = txn_repo.get_transaction(transaction_id)
        if txn:
            logger.info(f"Fetched transaction {txn.transaction_id} for customer {txn.customer_id}")
        if not txn:
            raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
        cust = txn_repo.get_customer_behavior(txn.customer_id)
        if cust:
            logger.info(f"Fetched customer profile {cust.customer_id}")
        if not cust:
            raise HTTPException(status_code=404, detail=f"Customer {txn.customer_id} profile not found")
        transactions_map = {txn.transaction_id: txn}
        customers_map = {cust.customer_id: cust}
    else:
        # Local filesystem mode: lazy load all data once
        global _transactions, _customers
        if not _transactions:
            data_dir = Path(settings.DATA_DIR)
            _transactions = load_transactions(data_dir / "transactions.csv")
            _customers = load_customer_behavior(data_dir / "customer_behavior.csv")
    
    # Validate transaction exists in local mode
    if settings.STORAGE_BACKEND != "dynamodb" and transaction_id not in _transactions:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    
    try:
        # Consolidate data
        if settings.STORAGE_BACKEND == "dynamodb":
            consolidated = consolidate(transaction_id, transactions_map, customers_map)
        else:
            if transaction_id not in _transactions:
                raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
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
        txn_repo, _, _ = _build_repositories(settings)
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
    
    txn_repo, _, _ = _build_repositories(settings)
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
    txn_repo: TransactionRepository = Depends(get_transaction_repo),
):
    """List all transactions with their latest decisions."""
    return txn_repo.list_transactions()


@router.get("/transactions/{transaction_id}", response_model=TransactionDetailResponse)
async def get_transaction_detail(
    transaction_id: str,
    txn_repo: TransactionRepository = Depends(get_transaction_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
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
    hitl_repo: HitlRepository = Depends(get_hitl_repo),
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
    txn_repo, audit_repo, hitl_repo = _build_repositories(settings)
    
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
