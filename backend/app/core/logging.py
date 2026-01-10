"""JSON structured logging configuration."""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "transaction_id"):
            log_data["transaction_id"] = record.transaction_id
        if hasattr(record, "agent"):
            log_data["agent"] = record.agent
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging() -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger("fraud_detection")
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger


# Global logger instance
logger = setup_logging()


def log_agent_event(
    agent: str,
    message: str,
    transaction_id: str | None = None,
    level: int = logging.INFO,
    **extra: Any
) -> None:
    """Log an agent-related event with structured data."""
    record = logging.LogRecord(
        name="fraud_detection",
        level=level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    record.agent = agent
    if transaction_id:
        record.transaction_id = transaction_id
    for key, value in extra.items():
        setattr(record, key, value)
    
    logger.handle(record)
