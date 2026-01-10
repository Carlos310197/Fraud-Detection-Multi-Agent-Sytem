"""Application configuration with environment variable support."""
import os
from typing import Literal
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment
    APP_ENV: Literal["local", "aws"] = "local"
    
    # Storage paths
    STORAGE_BACKEND: Literal["local_json", "dynamodb"] = "local_json"
    INPUT_DIR: str = "../.storage/input"        # Input data: CSVs, policies JSON
    PERSISTENCE_DIR: str = "../.storage/state"  # App state: audit trails, HITL cases, decisions
    VECTOR_DIR: str = "../.storage/vectors"     # ChromaDB embeddings database
    
    # Aliases for backward compatibility
    @property
    def DATA_DIR(self) -> str:
        return self.INPUT_DIR
    
    @property
    def STORE_DIR(self) -> str:
        return self.PERSISTENCE_DIR
    
    # LLM/Embeddings
    LLM_PROVIDER: Literal["mock", "openai", "bedrock"] = "mock"
    EMBEDDINGS_PROVIDER: Literal["mock", "openai", "bedrock"] = "mock"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDINGS_MODEL: str = "text-embedding-3-small"
    
    # Web Search
    WEB_SEARCH_PROVIDER: Literal["mock", "custom"] = "mock"
    WEB_MAX_RESULTS: int = 3
    WEB_ALLOWLIST_DOMAINS: str = "example.com,owasp.org,mitre.org"
    
    # AWS (for future deployment)
    AWS_REGION: str = "us-east-1"
    DDB_TABLE_TRANSACTIONS: str = "fraud_transactions"
    DDB_TABLE_AUDIT: str = "fraud_audit"
    DDB_TABLE_HITL: str = "fraud_hitl"
    OPENSEARCH_COLLECTION_ENDPOINT: str = ""
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    BEDROCK_EMBEDDINGS_MODEL_ID: str = "amazon.titan-embed-text-v1"
    
    class Config:
        env_file = ".env"
        extra = "ignore"
    
    @property
    def allowlist_domains(self) -> set[str]:
        """Parse allowlist domains from comma-separated string."""
        return set(d.strip() for d in self.WEB_ALLOWLIST_DOMAINS.split(",") if d.strip())


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
