"""Index fraud policies into the vector store."""
from app.api.schemas import FraudPolicy
from app.rag.vector_store import VectorStore, Document
from app.core.logging import logger


def index_policies(policies: list[FraudPolicy], vector_store: VectorStore) -> int:
    """
    Index fraud policies into the vector store.
    
    Each policy becomes a single document with chunk_id="1".
    
    Args:
        policies: List of FraudPolicy objects
        vector_store: VectorStore instance
        
    Returns:
        Number of policies indexed
    """
    documents = []
    
    for policy in policies:
        # Create document ID: policy_id:version:chunk_id
        doc_id = f"{policy.policy_id}:{policy.version}:1"
        
        # Content is the rule text
        content = policy.rule
        
        # Metadata for retrieval
        metadata = {
            "policy_id": policy.policy_id,
            "version": policy.version,
            "chunk_id": "1"
        }
        
        documents.append(Document(
            doc_id=doc_id,
            content=content,
            metadata=metadata
        ))
    
    # Upsert all documents
    vector_store.upsert_documents(documents)
    
    logger.info(f"Indexed {len(policies)} policies into vector store")
    return len(policies)
