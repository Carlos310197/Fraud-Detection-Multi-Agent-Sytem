"""Custom exceptions for the fraud detection system."""
from typing import Any


class FraudDetectionError(Exception):
    """Base exception for fraud detection errors."""
    
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class TransactionNotFoundError(FraudDetectionError):
    """Raised when a transaction is not found."""
    
    def __init__(self, transaction_id: str):
        super().__init__(
            f"Transaction not found: {transaction_id}",
            {"transaction_id": transaction_id}
        )


class CustomerNotFoundError(FraudDetectionError):
    """Raised when a customer is not found."""
    
    def __init__(self, customer_id: str):
        super().__init__(
            f"Customer not found: {customer_id}",
            {"customer_id": customer_id}
        )


class DataLoadError(FraudDetectionError):
    """Raised when data loading fails."""
    
    def __init__(self, source: str, reason: str):
        super().__init__(
            f"Failed to load data from {source}: {reason}",
            {"source": source, "reason": reason}
        )


class AgentExecutionError(FraudDetectionError):
    """Raised when an agent fails during execution."""
    
    def __init__(self, agent_name: str, reason: str, transaction_id: str | None = None):
        super().__init__(
            f"Agent '{agent_name}' failed: {reason}",
            {"agent_name": agent_name, "reason": reason, "transaction_id": transaction_id}
        )


class HITLCaseNotFoundError(FraudDetectionError):
    """Raised when a HITL case is not found."""
    
    def __init__(self, case_id: str):
        super().__init__(
            f"HITL case not found: {case_id}",
            {"case_id": case_id}
        )


class VectorStoreError(FraudDetectionError):
    """Raised when vector store operations fail."""
    
    def __init__(self, operation: str, reason: str):
        super().__init__(
            f"Vector store {operation} failed: {reason}",
            {"operation": operation, "reason": reason}
        )
