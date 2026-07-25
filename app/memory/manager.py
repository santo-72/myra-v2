import chromadb
import structlog
import os
from typing import List, Dict, Any

logger = structlog.get_logger(__name__)

class MemoryManager:
    def __init__(self, persist_directory: str = "data/chroma"):
        os.makedirs(persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name="assistant_memory")
        logger.info("memory_manager_initialized", path=persist_directory)

    def remember_fact(self, text: str, metadata: Dict[str, Any] = None):
        if metadata is None:
            metadata = {}
            
        # Simple ID generation based on count
        doc_id = f"fact_{self.collection.count() + 1}"
        
        try:
            self.collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            logger.debug("fact_remembered", doc_id=doc_id)
        except Exception as e:
            logger.error("remember_fact_error", error=str(e))

    def recall_facts(self, query: str, n_results: int = 3) -> List[str]:
        if self.collection.count() == 0:
            return []
            
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, self.collection.count())
            )
            return results['documents'][0] if results['documents'] else []
        except Exception as e:
            logger.error("recall_facts_error", error=str(e))
            return []
