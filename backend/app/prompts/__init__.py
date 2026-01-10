"""Centralized prompts for multi-agent fraud detection system."""
from app.prompts.loader import (
    get_prompt_loader,
    get_debate_pro_fraud_prompts,
    get_debate_pro_customer_prompts,
    get_customer_explanation_prompts,
    get_audit_explanation_prompts,
    PromptLoader,
    PromptNotFoundError,
    PromptValidationError,
)

__all__ = [
    # Loader
    "get_prompt_loader",
    "PromptLoader",
    "PromptNotFoundError",
    "PromptValidationError",
    # Convenience functions
    "get_debate_pro_fraud_prompts",
    "get_debate_pro_customer_prompts",
    "get_customer_explanation_prompts",
    "get_audit_explanation_prompts",
]
