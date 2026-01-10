"""Application configuration with environment variable support."""
import os
from typing import Literal
from pydantic_settings import BaseSettings
from functools import lru_cache


def _get_openai_api_key() -> str:
    """Fetch OpenAI API key from environment or AWS Systems Manager Parameter Store."""
    # First check if it's directly in environment (for testing)
    if api_key := os.getenv("OPENAI_API_KEY"):
        return api_key
    
    # If running on AWS Lambda, fetch from Parameter Store
    param_name = os.getenv("OPENAI_KEY_PARAMETER_NAME")
    if param_name:
        try:
            import boto3
            ssm = boto3.client("ssm", region_name=os.getenv("AWS_REGION", "us-east-1"))
            response = ssm.get_parameter(Name=param_name, WithDecryption=True)
            return response["Parameter"]["Value"]
        except Exception as e:
            # Log but don't crash - OpenAI might not be needed
            print(f"Warning: Failed to fetch OpenAI key from Parameter Store: {e}")
    
    return ""


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
    
    def __init__(self, **data):
        """Initialize settings, fetching API key from Parameter Store if needed."""
        super().__init__(**data)
        # Override OPENAI_API_KEY with runtime fetch if not already set
        if not self.OPENAI_API_KEY:
            self.OPENAI_API_KEY = _get_openai_api_key()
    
    # Web Search
    WEB_SEARCH_PROVIDER: Literal["mock", "custom"] = "mock"
    WEB_MAX_RESULTS: int = 3
    WEB_ALLOWLIST_DOMAINS: str = "example.com,owasp.org,mitre.org"
    
    # AWS (for future deployment)
    AWS_REGION: str = "us-east-1"
    INPUT_BUCKET: str = ""  # S3 bucket for input files (AWS mode)
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
