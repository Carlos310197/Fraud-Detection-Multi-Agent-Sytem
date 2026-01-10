"""Abstract interfaces for storage repositories."""
from abc import ABC, abstractmethod
from typing import Any

from app.api.schemas import (
    Transaction,
    CustomerBehavior,
    DecisionResponse,
    AuditEvent,
    HitlCase,
    TransactionSummary,
)


class TransactionRepository(ABC):
    """Abstract interface for transaction storage."""
    
    @abstractmethod
    def save_transaction(self, transaction: Transaction) -> None:
        """Save or update a transaction."""
        pass
    
    @abstractmethod
    def get_transaction(self, transaction_id: str) -> Transaction | None:
        """Get a transaction by ID."""
        pass
    
    @abstractmethod
    def list_transactions(self) -> list[TransactionSummary]:
        """List all transactions with summaries."""
        pass
    
    @abstractmethod
    def save_decision(self, transaction_id: str, decision: DecisionResponse) -> None:
        """Save the decision for a transaction."""
        pass
    
    @abstractmethod
    def get_decision(self, transaction_id: str) -> DecisionResponse | None:
        """Get the latest decision for a transaction."""
        pass
    
    @abstractmethod
    def save_customer_behavior(self, customer: CustomerBehavior) -> None:
        """Save or update a customer behavior profile."""
        pass
    
    @abstractmethod
    def get_customer_behavior(self, customer_id: str) -> CustomerBehavior | None:
        """Get a customer behavior profile by ID."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all stored data."""
        pass


class AuditRepository(ABC):
    """Abstract interface for audit event storage."""
    
    @abstractmethod
    def append_event(self, event: AuditEvent) -> None:
        """Append an audit event."""
        pass
    
    @abstractmethod
    def get_events(self, transaction_id: str) -> list[AuditEvent]:
        """Get all audit events for a transaction."""
        pass
    
    @abstractmethod
    def get_next_seq(self, transaction_id: str) -> int:
        """Get the next sequence number for a transaction."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all audit data."""
        pass


class HitlRepository(ABC):
    """Abstract interface for HITL case storage."""
    
    @abstractmethod
    def create_case(self, case: HitlCase) -> None:
        """Create a new HITL case."""
        pass
    
    @abstractmethod
    def get_case(self, case_id: str) -> HitlCase | None:
        """Get a HITL case by ID."""
        pass
    
    @abstractmethod
    def get_case_by_transaction(self, transaction_id: str) -> HitlCase | None:
        """Get a HITL case by transaction ID."""
        pass
    
    @abstractmethod
    def list_open_cases(self) -> list[HitlCase]:
        """List all open HITL cases."""
        pass
    
    @abstractmethod
    def resolve_case(self, case_id: str, resolution: dict[str, Any], resolved_at: str) -> None:
        """Resolve a HITL case."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all HITL data."""
        pass
