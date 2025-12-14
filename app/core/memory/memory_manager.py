# app/core/memory/memory_manager.py
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

class MemoryManager:
    """Simple session-based memory management"""
    
    def __init__(self):
        # Short-term memory (current session only - in-memory)
        self.short_term: Dict[str, List[Dict]] = {}
        
        # Memory limits
        self.max_short_term = 10  # Last 10 interactions per session
    
    def add_interaction(self, user_id: str, query: str, response: str, tool_data: Dict = None):
        """Add interaction to short-term memory"""
        if user_id not in self.short_term:
            self.short_term[user_id] = []
        
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response,
            "tool_data": tool_data or {}
        }
        
        self.short_term[user_id].append(interaction)
        
        # Keep only recent interactions
        if len(self.short_term[user_id]) > self.max_short_term:
            self.short_term[user_id] = self.short_term[user_id][-self.max_short_term:]
    
    def get_recent_context(self, user_id: str, limit: int = 3) -> str:
        """Get recent conversation context"""
        if user_id not in self.short_term:
            return ""
        
        recent = self.short_term[user_id][-limit:]
        context_parts = []
        
        for interaction in recent:
            context_parts.append(f"Previous: {interaction['query']} → {interaction['response'][:100]}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def clear_session(self, user_id: str):
        """Clear session memory for user"""
        if user_id in self.short_term:
            del self.short_term[user_id]
    
    def get_session_stats(self, user_id: str) -> Dict[str, Any]:
        """Get current session statistics"""
        if user_id not in self.short_term:
            return {"total_interactions": 0}
        
        return {
            "total_interactions": len(self.short_term[user_id]),
            "session_active": True
        }