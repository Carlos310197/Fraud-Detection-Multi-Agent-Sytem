"""Embedder implementations for text embedding."""
import hashlib
from abc import ABC, abstractmethod


class Embedder(ABC):
    """Abstract interface for text embedders."""
    
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """
        Embed a single query text.
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding vector
        """
        pass


class MockEmbedder(Embedder):
    """
    Deterministic mock embedder using SHA256 hash.
    
    Produces consistent embeddings based on text content,
    useful for testing and local development without API calls.
    """
    
    def __init__(self, dimension: int = 256):
        """
        Initialize the mock embedder.
        
        Args:
            dimension: Output embedding dimension
        """
        self.dimension = dimension
    
    def _text_to_embedding(self, text: str) -> list[float]:
        """
        Convert text to a deterministic embedding vector.
        
        Uses SHA256 hash expanded to fill the dimension.
        """
        # Get SHA256 hash bytes
        hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
        
        # Expand hash to fill dimension by repeating
        expanded_bytes = (hash_bytes * (self.dimension // len(hash_bytes) + 1))[:self.dimension]
        
        # Convert bytes to floats in range [-1, 1]
        embedding = []
        for byte in expanded_bytes:
            # Map byte (0-255) to float (-1 to 1)
            value = (byte / 127.5) - 1.0
            embedding.append(value)
        
        return embedding
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts."""
        return [self._text_to_embedding(text) for text in texts]
    
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        return self._text_to_embedding(text)


class OpenAIEmbedder(Embedder):
    """
    OpenAI embedder using text-embedding models.
    """
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        """
        Initialize the OpenAI embedder.
        
        Args:
            api_key: OpenAI API key
            model: Embedding model name
        """
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts using OpenAI."""
        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [item.embedding for item in response.data]
    
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        response = self.client.embeddings.create(
            model=self.model,
            input=[text]
        )
        return response.data[0].embedding


class BedrockEmbedder(Embedder):
    """
    AWS Bedrock embedder using Titan embeddings.
    
    For use in AWS deployment.
    """
    
    def __init__(self, model_id: str = "amazon.titan-embed-text-v1", region: str = "us-east-1"):
        """
        Initialize the Bedrock embedder.
        
        Args:
            model_id: Bedrock embedding model ID
            region: AWS region
        """
        self.model_id = model_id
        self.region = region
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of Bedrock client."""
        if self._client is None:
            import boto3
            self._client = boto3.client(
                service_name="bedrock-runtime",
                region_name=self.region
            )
        return self._client
    
    def _embed_single(self, text: str) -> list[float]:
        """Embed a single text using Bedrock."""
        import json
        
        body = json.dumps({"inputText": text})
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=body,
            contentType="application/json",
            accept="application/json"
        )
        
        result = json.loads(response["body"].read())
        return result["embedding"]
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts."""
        return [self._embed_single(text) for text in texts]
    
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        return self._embed_single(text)


def get_embedder(provider: str = "mock", settings=None, **kwargs) -> Embedder:
    """
    Factory function to get an embedder based on provider.
    
    Args:
        provider: "mock", "openai", or "bedrock"
        settings: Application settings (for API keys)
        **kwargs: Additional arguments for the embedder
        
    Returns:
        Embedder instance
    """
    if provider == "mock":
        return MockEmbedder(**kwargs)
    elif provider == "openai":
        if settings and settings.OPENAI_API_KEY:
            return OpenAIEmbedder(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_EMBEDDINGS_MODEL,
            )
        raise ValueError("OpenAI embedder requires OPENAI_API_KEY in settings")
    elif provider == "bedrock":
        if settings:
            return BedrockEmbedder(
                model_id=settings.BEDROCK_EMBEDDINGS_MODEL_ID,
                region=settings.AWS_REGION,
            )
        return BedrockEmbedder(**kwargs)
    else:
        raise ValueError(f"Unknown embedder provider: {provider}")
