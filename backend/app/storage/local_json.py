"""Local JSON file-based storage implementation."""
import json
import os
from pathlib import Path
from typing import Any
from filelock import FileLock

from app.api.schemas import (
    Transaction,
    CustomerBehavior,
    DecisionResponse,
    AuditEvent,
    HitlCase,
    TransactionSummary,
)
from app.storage.interfaces import TransactionRepository, AuditRepository, HitlRepository
from app.core.logging import logger


class LocalJSONTransactionRepository(TransactionRepository):
    """File-based transaction repository using JSON."""
    
    def __init__(self, store_dir: str):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        
        self.transactions_file = self.store_dir / "transactions_index.json"
        self.customers_file = self.store_dir / "customers_index.json"
        self.decisions_file = self.store_dir / "decisions_index.json"
        
        self._init_files()
    
    def _init_files(self) -> None:
        """Initialize JSON files if they don't exist."""
        for filepath in [self.transactions_file, self.customers_file, self.decisions_file]:
            if not filepath.exists():
                with open(filepath, "w") as f:
                    json.dump({}, f)
    
    def _read_json(self, filepath: Path) -> dict:
        """Read and return JSON file content with locking."""
        lock = FileLock(str(filepath) + ".lock")
        with lock:
            with open(filepath, "r") as f:
                return json.load(f)
    
    def _write_json(self, filepath: Path, data: dict) -> None:
        """Write data to JSON file with locking."""
        lock = FileLock(str(filepath) + ".lock")
        with lock:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
    
    def save_transaction(self, transaction: Transaction) -> None:
        """Save or update a transaction."""
        data = self._read_json(self.transactions_file)
        data[transaction.transaction_id] = transaction.model_dump()
        self._write_json(self.transactions_file, data)
    
    def get_transaction(self, transaction_id: str) -> Transaction | None:
        """Get a transaction by ID."""
        data = self._read_json(self.transactions_file)
        if transaction_id in data:
            return Transaction(**data[transaction_id])
        return None
    
    def list_transactions(self) -> list[TransactionSummary]:
        """List all transactions with summaries."""
        transactions_data = self._read_json(self.transactions_file)
        decisions_data = self._read_json(self.decisions_file)
        
        summaries = []
        for txn_id, txn_data in transactions_data.items():
            decision_data = decisions_data.get(txn_id)
            summaries.append(TransactionSummary(
                transaction_id=txn_data["transaction_id"],
                customer_id=txn_data["customer_id"],
                amount=txn_data["amount"],
                currency=txn_data["currency"],
                timestamp=txn_data["timestamp"],
                decision=decision_data["decision"] if decision_data else None,
                confidence=decision_data["confidence"] if decision_data else None,
            ))
        return summaries
    
    def save_decision(self, transaction_id: str, decision: DecisionResponse) -> None:
        """Save the decision for a transaction."""
        data = self._read_json(self.decisions_file)
        data[transaction_id] = decision.model_dump()
        self._write_json(self.decisions_file, data)
    
    def get_decision(self, transaction_id: str) -> DecisionResponse | None:
        """Get the latest decision for a transaction."""
        data = self._read_json(self.decisions_file)
        if transaction_id in data:
            return DecisionResponse(**data[transaction_id])
        return None
    
    def save_customer_behavior(self, customer: CustomerBehavior) -> None:
        """Save or update a customer behavior profile."""
        data = self._read_json(self.customers_file)
        data[customer.customer_id] = customer.model_dump()
        self._write_json(self.customers_file, data)
    
    def get_customer_behavior(self, customer_id: str) -> CustomerBehavior | None:
        """Get a customer behavior profile by ID."""
        data = self._read_json(self.customers_file)
        if customer_id in data:
            return CustomerBehavior(**data[customer_id])
        return None
    
    def clear(self) -> None:
        """Clear all stored data."""
        for filepath in [self.transactions_file, self.customers_file, self.decisions_file]:
            with open(filepath, "w") as f:
                json.dump({}, f)


class LocalJSONAuditRepository(AuditRepository):
    """File-based audit repository using JSONL files."""
    
    def __init__(self, store_dir: str):
        self.store_dir = Path(store_dir)
        self.audit_dir = self.store_dir / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_audit_file(self, transaction_id: str) -> Path:
        """Get the audit file path for a transaction."""
        return self.audit_dir / f"{transaction_id}.jsonl"
    
    def append_event(self, event: AuditEvent) -> None:
        """Append an audit event."""
        filepath = self._get_audit_file(event.transaction_id)
        lock = FileLock(str(filepath) + ".lock")
        with lock:
            with open(filepath, "a") as f:
                f.write(json.dumps(event.model_dump()) + "\n")
    
    def get_events(self, transaction_id: str) -> list[AuditEvent]:
        """Get all audit events for a transaction."""
        filepath = self._get_audit_file(transaction_id)
        events = []
        
        if filepath.exists():
            lock = FileLock(str(filepath) + ".lock")
            with lock:
                with open(filepath, "r") as f:
                    for line in f:
                        if line.strip():
                            events.append(AuditEvent(**json.loads(line)))
        
        return sorted(events, key=lambda e: e.seq)
    
    def get_next_seq(self, transaction_id: str) -> int:
        """Get the next sequence number for a transaction."""
        events = self.get_events(transaction_id)
        if events:
            return max(e.seq for e in events) + 1
        return 1
    
    def clear(self) -> None:
        """Clear all audit data."""
        for filepath in self.audit_dir.glob("*.jsonl"):
            filepath.unlink()


class LocalJSONHitlRepository(HitlRepository):
    """File-based HITL case repository using JSON."""
    
    def __init__(self, store_dir: str):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        
        self.cases_file = self.store_dir / "hitl_cases.json"
        self._init_file()
    
    def _init_file(self) -> None:
        """Initialize JSON file if it doesn't exist."""
        if not self.cases_file.exists():
            with open(self.cases_file, "w") as f:
                json.dump([], f)
    
    def _read_cases(self) -> list[dict]:
        """Read all cases from file."""
        lock = FileLock(str(self.cases_file) + ".lock")
        with lock:
            with open(self.cases_file, "r") as f:
                return json.load(f)
    
    def _write_cases(self, cases: list[dict]) -> None:
        """Write cases to file."""
        lock = FileLock(str(self.cases_file) + ".lock")
        with lock:
            with open(self.cases_file, "w") as f:
                json.dump(cases, f, indent=2)
    
    def create_case(self, case: HitlCase) -> None:
        """Create a new HITL case."""
        cases = self._read_cases()
        cases.append(case.model_dump())
        self._write_cases(cases)
    
    def get_case(self, case_id: str) -> HitlCase | None:
        """Get a HITL case by ID."""
        cases = self._read_cases()
        for case in cases:
            if case["case_id"] == case_id:
                return HitlCase(**case)
        return None
    
    def get_case_by_transaction(self, transaction_id: str) -> HitlCase | None:
        """Get a HITL case by transaction ID."""
        cases = self._read_cases()
        for case in cases:
            if case["transaction_id"] == transaction_id:
                return HitlCase(**case)
        return None
    
    def list_open_cases(self) -> list[HitlCase]:
        """List all open HITL cases."""
        cases = self._read_cases()
        return [HitlCase(**c) for c in cases if c["status"] == "OPEN"]
    
    def resolve_case(self, case_id: str, resolution: dict[str, Any], resolved_at: str) -> None:
        """Resolve a HITL case."""
        cases = self._read_cases()
        for case in cases:
            if case["case_id"] == case_id:
                case["status"] = "RESOLVED"
                case["resolution"] = resolution
                case["resolved_at"] = resolved_at
                break
        self._write_cases(cases)
    
    def clear(self) -> None:
        """Clear all HITL data."""
        with open(self.cases_file, "w") as f:
            json.dump([], f)
