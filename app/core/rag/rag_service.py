# app/core/rag/rag_service.py
from typing import List, Dict, Any
from .knowledge_base import KnowledgeBase
import logging

logger = logging.getLogger(__name__)

class RAGService:
    """RAG service for enhancing responses with knowledge"""
    
    def __init__(self):
        self.kb = KnowledgeBase()
    
    def enhance_response(self, query: str, tool_data: Dict[str, Any] = None) -> str:
        """Enhance response with relevant knowledge"""
        try:
            # Search for relevant knowledge
            relevant_docs = self.kb.search(query, k=2)
            
            if not relevant_docs:
                return ""
            
            # Filter high-quality results
            good_results = [doc for doc in relevant_docs if doc["score"] > 0.3]
            
            if not good_results:
                return ""
            
            # Format knowledge for inclusion
            knowledge_text = " ".join([doc["content"] for doc in good_results])
            return f"\n\n💡 Tip: {knowledge_text}"
            
        except Exception as e:
            logger.error(f"RAG enhancement error: {str(e)}")
            return ""
    
    def get_contextual_advice(self, items: List[str], context: str = "general") -> str:
        """Get contextual advice for specific items"""
        if not items:
            return ""
        
        # Create query from items
        query = f"{context} advice for {', '.join(items[:3])}"
        
        try:
            relevant_docs = self.kb.search(query, k=1)
            if relevant_docs and relevant_docs[0]["score"] > 0.2:
                return f"\n\n💡 {relevant_docs[0]['content']}"
        except Exception as e:
            logger.error(f"Contextual advice error: {str(e)}")
        
        return ""