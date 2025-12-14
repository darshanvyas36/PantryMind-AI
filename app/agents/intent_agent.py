# app/agents/intent_agent.py
from typing import Dict, Any
from .base import BaseAgent, AgentResult
import json

class IntentAgent(BaseAgent):
    def __init__(self, model_name: str = "qwen-2.5-7b-instruct"):
        super().__init__("IntentAgent", model_name)
        
    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        message = input_data.get("message", "")
        
        # Simple rule-based classification for common patterns
        message_lower = message.lower().strip()
        
        # Direct mappings for high confidence
        if any(word in message_lower for word in ["inventory", "stock", "items", "pantry"]):
            if any(word in message_lower for word in ["show", "list", "display", "what", "check"]):
                return AgentResult(
                    success=True,
                    data={"intent": "inventory_list", "confidence": 0.9},
                    confidence=0.9,
                    metadata={"classification": "rule_based"}
                )
            elif any(word in message_lower for word in ["add", "put", "store"]):
                return AgentResult(
                    success=True,
                    data={"intent": "inventory_add", "confidence": 0.9},
                    confidence=0.9,
                    metadata={"classification": "rule_based"}
                )
        
        # Category-specific queries
        if any(word in message_lower for word in ["vegetables", "fruits", "dairy", "meat", "grains"]):
            if any(word in message_lower for word in ["show", "list", "display", "what", "i have", "have"]):
                return AgentResult(
                    success=True,
                    data={"intent": "inventory_category", "confidence": 0.9},
                    confidence=0.9,
                    metadata={"classification": "category_filter"}
                )
        
        # Consumption/usage queries
        if any(word in message_lower for word in ["consume", "use", "take", "remove"]):
            return AgentResult(
                success=True,
                data={"intent": "inventory_consume", "confidence": 0.9},
                confidence=0.9,
                metadata={"classification": "consumption"}
            )
        
        if any(word in message_lower for word in ["recipe", "cook", "make", "meal"]):
            return AgentResult(
                success=True,
                data={"intent": "recipe", "confidence": 0.9},
                confidence=0.9,
                metadata={"classification": "rule_based"}
            )
        
        if any(word in message_lower for word in ["shopping", "buy", "purchase"]):
            return AgentResult(
                success=True,
                data={"intent": "shopping_list", "confidence": 0.9},
                confidence=0.9,
                metadata={"classification": "rule_based"}
            )
        
        if message_lower in ["hello", "hi", "hey"]:
            return AgentResult(
                success=True,
                data={"intent": "greeting", "confidence": 1.0},
                confidence=1.0,
                metadata={"classification": "exact_match"}
            )
        
        if any(word in message_lower for word in ["help", "assist", "guide"]):
            return AgentResult(
                success=True,
                data={"intent": "help", "confidence": 0.9},
                confidence=0.9,
                metadata={"classification": "rule_based"}
            )
        
        # General show/list queries
        if any(word in message_lower for word in ["show", "list", "display"]):
            return AgentResult(
                success=True,
                data={"intent": "inventory_list", "confidence": 0.7},
                confidence=0.7,
                metadata={"classification": "general_show"}
            )
        
        # Fallback for unclear intents
        return AgentResult(
            success=True,
            data={"intent": "help", "confidence": 0.3},
            confidence=0.3,
            metadata={"classification": "fallback"}
        )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "input_schema": {
                "message": {"type": "string", "required": True}
            },
            "output_schema": {
                "intent": {"type": "string", "enum": ["inventory", "recipe", "ocr", "analytics", "help"]},
                "confidence": {"type": "float", "range": [0.0, 1.0]}
            },
            "preconditions": ["message must not be empty"],
            "side_effects": []
        }