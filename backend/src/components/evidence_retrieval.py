"""
Component 3 — Evidence Retrieval System.
Searches local text/JSON evidence files using hybrid vector retrieval (FAISS CPU / SentenceTransformers)
with a deterministic keyword fallback for CPU efficiency.
"""

from typing import List, Dict, Any, Optional
import math
from src.utils.logger import get_logger

logger = get_logger("EvidenceRetrieval")

class EvidenceRetrievalEngine:
    """Retrieves relevant evidence documents for a given dispute query."""
    
    def __init__(self, use_vector_search: bool = True):
        self.use_vector_search = use_vector_search
        self._faiss_available = False
        self._st_available = False
        
        if self.use_vector_search:
            try:
                import faiss
                from sentence_transformers import SentenceTransformer
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
                self._faiss = faiss
                self._faiss_available = True
                self._st_available = True
                logger.info("SentenceTransformers & FAISS CPU initialized successfully.")
            except ImportError:
                logger.info("Vector search libraries unavailable. Operating with TF-IDF/Keyword fallback.")
                
    def retrieve(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top_k relevant documents for the given search query.
        """
        if not documents:
            return []
            
        if self._faiss_available and self._st_available and len(documents) > 1:
            try:
                return self._vector_retrieve(query, documents, top_k)
            except Exception as e:
                logger.warning(f"Vector search failed ({e}), falling back to deterministic text search.")
                
        return self._keyword_retrieve(query, documents, top_k)
        
    def _keyword_retrieve(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Fast, zero-dependency TF-IDF / term-overlap document retrieval."""
        query_terms = set(query.lower().split())
        scored_docs = []
        
        for doc in documents:
            content = str(doc.get("content", "")) + " " + str(doc.get("document_type", ""))
            doc_terms = content.lower().split()
            
            if not doc_terms:
                score = 0.0
            else:
                matches = sum(1 for t in query_terms if t in doc_terms)
                score = matches / math.sqrt(len(doc_terms) + 1)
                
            scored_docs.append((score, doc))
            
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_docs[:top_k]]
        
    def _vector_retrieve(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Dense embedding vector search using SentenceTransformers + FAISS CPU."""
        corpus_texts = [
            f"{doc.get('document_type', '')}: {doc.get('content', '')}"
            for doc in documents
        ]
        
        corpus_embeddings = self.embedder.encode(corpus_texts, convert_to_numpy=True)
        query_embedding = self.embedder.encode([query], convert_to_numpy=True)
        
        dimension = corpus_embeddings.shape[1]
        index = self._faiss.IndexFlatL2(dimension)
        index.add(corpus_embeddings.astype('float32'))
        
        k = min(top_k, len(documents))
        distances, indices = index.search(query_embedding.astype('float32'), k)
        
        retrieved = []
        for idx in indices[0]:
            if 0 <= idx < len(documents):
                retrieved.append(documents[idx])
                
        return retrieved
