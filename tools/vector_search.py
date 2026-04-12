"""
Vector Search Module - ChromaDB Integration
============================================
Semantic search using vector embeddings.
"""

import chromadb
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class VectorResult:
    """Result from vector search"""
    content: str
    source: str
    section: str
    score: float  # 0-1, higher = more similar


class VectorSearch:
    """ChromaDB-based vector search"""
    
    def __init__(self, persist_dir: str = "./chroma_data"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"✅ VectorSearch ready | Collection: documents")
    
    def index_documents(self, documents: List[Dict]) -> int:
        """Index documents into ChromaDB"""
        if not documents:
            return 0
        
        ids = [doc['id'] for doc in documents]
        contents = [doc['content'] for doc in documents]
        metadatas = [doc.get('metadata', {}) for doc in documents]
        
        self.collection.upsert(
            ids=ids,
            documents=contents,
            metadatas=metadatas
        )
        
        logger.info(f"📚 Indexed {len(documents)} documents")
        return len(documents)
    
    def search(self, query: str, top_k: int = 5) -> List[VectorResult]:
        """Perform semantic search"""
        if self.collection.count() == 0:
            return []
        
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, self.collection.count())
        )
        
        vector_results = []
        
        if results['documents'] and len(results['documents']) > 0:
            docs = results['documents'][0]
            metadatas = results['metadatas'][0] if results['metadatas'] else [None] * len(docs)
            distances = results['distances'][0] if 'distances' in results else [0] * len(docs)
            
            for i, doc in enumerate(docs):
                distance = distances[i] if i < len(distances) else 0
                score = round(1.0 - distance, 4)  # Convert to similarity
                
                metadata = metadatas[i] if i < len(metadatas) else {}
                
                if score >= 0.3:  # Minimum threshold
                    vector_results.append(VectorResult(
                        content=doc[:1000] + "..." if len(doc) > 1000 else doc,
                        source=metadata.get('source', 'unknown'),
                        section=metadata.get('section', 'unknown'),
                        score=score
                    ))
        
        return vector_results
    
    def get_stats(self) -> Dict:
        """Get collection statistics"""
        return {
            "total_documents": self.collection.count(),
            "persist_directory": str(self.persist_dir)
        }


# Global instance
_instance: Optional[VectorSearch] = None

def get_vector_search() -> VectorSearch:
    """Get or create singleton instance"""
    global _instance
    if _instance is None:
        from config import Config
        persist_dir = getattr(Config, 'CHROMA_PERSIST_DIR', './chroma_data')
        _instance = VectorSearch(persist_dir=persist_dir)
    return _instance
