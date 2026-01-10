"""YAML-based prompt loader with validation."""
import os
from pathlib import Path
from functools import lru_cache
from typing import Any

import yaml


class PromptNotFoundError(Exception):
    """Raised when a prompt template is not found."""
    pass


class PromptValidationError(Exception):
    """Raised when prompt template variables are missing."""
    pass


class PromptLoader:
    """
    Loads and manages prompts from YAML files.
    
    Features:
    - Language-specific prompt loading (es, en, etc.)
    - Variable substitution with validation
    - Caching for performance
    - Hot-reload support (optional)
    """
    
    def __init__(self, language: str = "es", prompts_dir: Path | None = None):
        """
        Initialize the prompt loader.
        
        Args:
            language: Language code for prompts (default: "es")
            prompts_dir: Base directory for prompts (default: ./prompts)
        """
        self.language = language
        self.prompts_dir = prompts_dir or Path(__file__).parent
        self._cache: dict[str, dict] = {}
        self._base_config: dict[str, Any] = {}
        self._load_base_config()
    
    def _load_base_config(self) -> None:
        """Load base configuration (system context, currency, etc.)."""
        base_file = self.prompts_dir / self.language / "base.yml"
        if base_file.exists():
            with open(base_file, "r", encoding="utf-8") as f:
                self._base_config = yaml.safe_load(f) or {}
    
    def _load_prompt_file(self, filename: str) -> dict:
        """Load a prompt file from the language directory."""
        if filename in self._cache:
            return self._cache[filename]
        
        file_path = self.prompts_dir / self.language / f"{filename}.yml"
        
        if not file_path.exists():
            raise PromptNotFoundError(f"Prompt file not found: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        self._cache[filename] = data
        return data
    
    def get_prompt(
        self,
        file: str,
        prompt_name: str,
        prompt_type: str = "user",
        **variables
    ) -> str:
        """
        Get a formatted prompt with variable substitution.
        
        Args:
            file: The prompt file name (without .yml)
            prompt_name: The prompt key within the file
            prompt_type: "system" or "user"
            **variables: Variables to substitute in the prompt
            
        Returns:
            Formatted prompt string
            
        Raises:
            PromptNotFoundError: If prompt not found
            PromptValidationError: If required variables missing
        """
        prompts = self._load_prompt_file(file)
        
        if prompt_name not in prompts:
            raise PromptNotFoundError(f"Prompt '{prompt_name}' not found in {file}.yml")
        
        prompt_data = prompts[prompt_name]
        
        if prompt_type not in prompt_data:
            raise PromptNotFoundError(f"Prompt type '{prompt_type}' not found in {file}.{prompt_name}")
        
        template = prompt_data[prompt_type]
        
        # Add base config variables (system_context, etc.)
        all_variables = {**self._base_config, **variables}
        
        try:
            return template.format(**all_variables)
        except KeyError as e:
            raise PromptValidationError(f"Missing variable in prompt: {e}")
    
    def get_system_prompt(self, file: str, prompt_name: str, **variables) -> str:
        """Convenience method to get system prompt."""
        return self.get_prompt(file, prompt_name, "system", **variables)
    
    def get_user_prompt(self, file: str, prompt_name: str, **variables) -> str:
        """Convenience method to get user prompt."""
        return self.get_prompt(file, prompt_name, "user", **variables)
    
    def reload(self) -> None:
        """Clear cache and reload all prompts (for hot-reload)."""
        self._cache.clear()
        self._load_base_config()
    
    @property
    def system_context(self) -> str:
        """Get the base system context."""
        return self._base_config.get("system_context", "")
    
    @property
    def currency_symbol(self) -> str:
        """Get the currency symbol."""
        return self._base_config.get("currency_symbol", "$")


# Global instance with default language
_loader: PromptLoader | None = None


def get_prompt_loader(language: str = "es") -> PromptLoader:
    """Get or create the global prompt loader."""
    global _loader
    if _loader is None or _loader.language != language:
        _loader = PromptLoader(language=language)
    return _loader


# Convenience functions for direct access
def get_debate_pro_fraud_prompts(**variables) -> tuple[str, str]:
    """Get Pro-Fraud debate prompts (system, user)."""
    loader = get_prompt_loader()
    return (
        loader.get_system_prompt("debate", "pro_fraud", **variables),
        loader.get_user_prompt("debate", "pro_fraud", **variables),
    )


def get_debate_pro_customer_prompts(**variables) -> tuple[str, str]:
    """Get Pro-Customer debate prompts (system, user)."""
    loader = get_prompt_loader()
    return (
        loader.get_system_prompt("debate", "pro_customer", **variables),
        loader.get_user_prompt("debate", "pro_customer", **variables),
    )


def get_customer_explanation_prompts(**variables) -> tuple[str, str]:
    """Get customer explanation prompts (system, user)."""
    loader = get_prompt_loader()
    return (
        loader.get_system_prompt("explainability", "customer", **variables),
        loader.get_user_prompt("explainability", "customer", **variables),
    )


def get_audit_explanation_prompts(**variables) -> tuple[str, str]:
    """Get audit explanation prompts (system, user)."""
    loader = get_prompt_loader()
    return (
        loader.get_system_prompt("explainability", "audit", **variables),
        loader.get_user_prompt("explainability", "audit", **variables),
    )
