"""LLM service for agent reasoning."""
import json
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from app.core.logging import logger

if TYPE_CHECKING:
    from app.core.config import Settings


class LLMService(ABC):
    """Abstract interface for LLM services."""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None, max_tokens: int = 1000) -> str:
        """Generate text from a prompt."""
        pass
    
    @abstractmethod
    def generate_structured(self, prompt: str, schema: dict, system_prompt: str | None = None) -> dict:
        """Generate structured output matching a schema."""
        pass


class MockLLMService(LLMService):
    """Mock LLM service that returns deterministic responses."""
    
    def generate(self, prompt: str, system_prompt: str | None = None, max_tokens: int = 1000) -> str:
        """Return a mock response."""
        return "Mock LLM response"
    
    def generate_structured(self, prompt: str, schema: dict, system_prompt: str | None = None) -> dict:
        """Return mock structured data."""
        return {}


class OpenAILLMService(LLMService):
    """OpenAI LLM service."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
        logger.info(f"OpenAI LLM service initialized with model: {model}")
    
    def generate(self, prompt: str, system_prompt: str | None = None, max_tokens: int = 1000) -> str:
        """Generate text using OpenAI."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI LLM generation failed: {e}")
            raise
    
    def generate_structured(self, prompt: str, schema: dict, system_prompt: str | None = None) -> dict:
        """Generate structured output using OpenAI with JSON mode."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt + "\n\nResponde SOLO con JSON válido."})
        else:
            messages.append({"role": "system", "content": "Responde SOLO con JSON válido."})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content or "{}"
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM JSON response: {content}")
                return {}
        except Exception as e:
            logger.error(f"OpenAI LLM structured generation failed: {e}")
            raise


def get_llm_service(settings: "Settings") -> LLMService | None:
    """
    Factory function to get an LLM service based on settings.
    
    Args:
        settings: Application settings
        
    Returns:
        LLMService instance or None if no API key is configured
    """
    if settings.OPENAI_API_KEY:
        logger.info(f"Using OpenAI LLM service with model: {settings.OPENAI_MODEL}")
        return OpenAILLMService(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL
        )
    else:
        logger.warning("No OPENAI_API_KEY configured, agents will use mock/rule-based logic")
        return None
