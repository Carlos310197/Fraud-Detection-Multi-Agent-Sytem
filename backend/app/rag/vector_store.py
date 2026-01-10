"""Vector store implementation using ChromaDB."""
from typing import Any
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.rag.embedder import Embedder
from app.core.errors import VectorStoreError
from app.core.logging import logger


class Document:
    """Simple document representation for vector store."""
    
    def __init__(
        self,
        doc_id: str,
        content: str,
        metadata: dict[str, Any] | None = None
    ):
        self.doc_id = doc_id
        self.content = content
        self.metadata = metadata or {}


class VectorStore:
    """
    ChromaDB-based vector store for document retrieval.
    """
    
    def __init__(
        self,
        persist_directory: str,
        collection_name: str,
        embedder: Embedder
    ):
        """
        Initialize the vector store.
        
        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of the collection
            embedder: Embedder instance for generating embeddings
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedder = embedder
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"Initialized vector store at {persist_directory}, collection: {collection_name}")
    
    def upsert_documents(self, docs: list[Document]) -> None:
        """
        Upsert documents into the vector store.
        
        Args:
            docs: List of Document objects to upsert
        """
        if not docs:
            return
        
        try:
            ids = [doc.doc_id for doc in docs]
            contents = [doc.content for doc in docs]
            metadatas = [doc.metadata for doc in docs]
            
            # Generate embeddings
            embeddings = self.embedder.embed_texts(contents)
            
            # Upsert to collection
            self.collection.upsert(
                ids=ids,
                documents=contents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info(f"Upserted {len(docs)} documents to vector store")
        
        except Exception as e:
            raise VectorStoreError("upsert", str(e))
    
    def query(self, text: str, top_k: int = 3) -> list[Document]:
        """
        Query the vector store for similar documents.
        
        Args:
            text: Query text
            top_k: Number of results to return
            
        Returns:
            List of Document objects sorted by similarity
        """
        try:
            # Generate query embedding
            query_embedding = self.embedder.embed_query(text)
            
            # Query collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Convert to Document objects
            documents = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    documents.append(Document(
                        doc_id=doc_id,
                        content=results["documents"][0][i] if results["documents"] else "",
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {}
                    ))
            
            return documents
        
        except Exception as e:
            raise VectorStoreError("query", str(e))
    
    def clear(self) -> None:
        """Clear all documents from the collection."""
        try:
            # Delete and recreate collection
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Cleared vector store")
        except Exception as e:
            raise VectorStoreError("clear", str(e))
    
    def count(self) -> int:
        """Get the number of documents in the collection."""
        return self.collection.count()
