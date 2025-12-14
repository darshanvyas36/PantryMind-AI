# app/core/rag/knowledge_base.py
import faiss
import numpy as np
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config.settings import settings
from typing import List, Dict, Any
import json
import os

class KnowledgeBase:
    """FAISS-based knowledge base for cooking and food knowledge"""
    
    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=settings.gemini_api_key
        )
        self.dimension = 768  # text-embedding-004 dimension
        self.index = faiss.IndexFlatIP(self.dimension)
        self.documents = []
        self.metadata = []
        
        # Initialize with cooking knowledge
        self._load_cooking_knowledge()
    
    def _load_cooking_knowledge(self):
        """Load basic cooking and food knowledge"""
        knowledge_data = [
            {
                "content": "Milk should be stored in the refrigerator and typically lasts 5-7 days past expiration date if properly stored. Signs of spoilage include sour smell and chunky texture.",
                "category": "food_safety",
                "tags": ["milk", "dairy", "storage", "expiration"]
            },
            {
                "content": "Bread can be frozen for up to 3 months. To use frozen bread, thaw at room temperature or toast directly from frozen. Store bread in cool, dry place.",
                "category": "food_storage", 
                "tags": ["bread", "freezing", "storage"]
            },
            {
                "content": "Pasta with vegetables is a versatile dish. Add garlic, olive oil, and herbs like basil or oregano. Cook pasta al dente and add vegetables in order of cooking time needed.",
                "category": "cooking_tips",
                "tags": ["pasta", "vegetables", "cooking", "recipe"]
            },
            {
                "content": "To reduce food waste, use the FIFO method (First In, First Out). Check expiration dates regularly and plan meals around items that expire soon.",
                "category": "waste_reduction",
                "tags": ["waste", "organization", "planning"]
            },
            {
                "content": "Vegetables should be stored in the crisper drawer of your refrigerator. Leafy greens last 3-7 days, root vegetables can last 2-4 weeks when stored properly.",
                "category": "food_storage",
                "tags": ["vegetables", "storage", "refrigerator"]
            },
            {
                "content": "When cooking with expiring ingredients, prioritize items that spoil fastest. Dairy and meat should be used first, followed by vegetables, then pantry staples.",
                "category": "cooking_tips",
                "tags": ["expiring", "priority", "cooking", "planning"]
            }
        ]
        
        # Add documents to knowledge base
        for item in knowledge_data:
            self.add_document(item["content"], item)
    
    def add_document(self, text: str, metadata: Dict[str, Any]):
        """Add a document to the knowledge base"""
        # Generate embedding using Google API
        embedding_list = self.embeddings.embed_documents([text])
        embedding = np.array(embedding_list).astype('float32')
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embedding)
        
        # Add to index
        self.index.add(embedding)
        self.documents.append(text)
        self.metadata.append(metadata)
    
    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant documents"""
        # Generate query embedding using Google API
        query_embedding_list = self.embeddings.embed_query(query)
        query_embedding = np.array([query_embedding_list]).astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, k)
        
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx != -1:  # Valid result
                results.append({
                    "content": self.documents[idx],
                    "metadata": self.metadata[idx],
                    "score": float(score),
                    "rank": i + 1
                })
        
        return results