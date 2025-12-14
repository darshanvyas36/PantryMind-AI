# app/agents/cost_optimizer.py
from typing import Dict, Any, Optional, Tuple
from enum import Enum
import hashlib
import re
from difflib import SequenceMatcher

class ExitGate(Enum):
    RULE_BASED = "rule_based"
    CACHED_INTENT = "cached_intent"
    SIMPLE_CRUD = "simple_crud"
    HIGH_CONFIDENCE = "high_confidence"
    DETERMINISTIC = "deterministic"

class CostOptimizer:
    def __init__(self):
        self.intent_cache = {}
        self.simple_patterns = {
            "inventory_list": [r"inventory.*items", r"what.*inventory", r"show.*inventory", r"list.*items"],
            "inventory_expiring": [r"expiring.*soon", r"items.*expiring", r"expired.*items", r"all.*expired"],
            "inventory_low_stock": [r"low.*stock", r"running.*low", r"almost.*empty"],
            "inventory_check": [r".*i have", r"check.*", r"how much.*", r"do.*have"],
            "inventory_add": [r"add \d+.*", r"put.*in.*pantry"],
            "greeting": [r"^(hi|hello|hey)$"],
            "help": [r"help", r"what.*can.*do"]
        }
        
    def should_exit_early(self, message: str, kitchen_id: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if request can exit early without LLM calls"""
        
        # Gate 1: Rule-based routing (0 LLM calls)
        rule_result = self._check_rule_based_exit(message)
        if rule_result:
            return True, rule_result
            
        # Gate 2: Intent caching (0 LLM calls)
        cached_result = self._check_cached_intent(message)
        if cached_result:
            return True, cached_result
            
        # Gate 3: Simple CRUD patterns (0 LLM calls)
        crud_result = self._check_simple_crud(message)
        if crud_result:
            return True, crud_result
            
        # Gate 4: Semantic similarity fallback (0 LLM calls)
        similarity_result = self._check_semantic_similarity(message)
        if similarity_result:
            return True, similarity_result
            
        return False, None
    
    def _check_rule_based_exit(self, message: str) -> Optional[Dict[str, Any]]:
        """Rule-first routing - no LLM needed"""
        message_lower = message.lower().strip()
        
        # Exact matches for common requests
        exact_matches = {
            "hello": {"intent": "greeting", "response": "Hello! 👋 I'm your PantryMind assistant. What can I help you with?"},
            "hi": {"intent": "greeting", "response": "Hi there! How can I help you manage your pantry today?"},
            "help": {"intent": "help", "response": "I can help you manage inventory, find recipes, process receipts, and analyze your pantry data."},
            "inventory": {"intent": "inventory_list", "action": "list_inventory"},
            "show inventory": {"intent": "inventory_list", "action": "list_inventory"},
            "list items": {"intent": "inventory_list", "action": "list_inventory"}
        }
        
        if message_lower in exact_matches:
            result = exact_matches[message_lower]
            result["exit_gate"] = ExitGate.RULE_BASED
            result["llm_calls"] = 0
            return result
            
        return None
    
    def _check_cached_intent(self, message: str) -> Optional[Dict[str, Any]]:
        """Check if we've seen this utterance before"""
        message_hash = hashlib.md5(message.lower().encode()).hexdigest()
        
        if message_hash in self.intent_cache:
            cached = self.intent_cache[message_hash]
            cached["exit_gate"] = ExitGate.CACHED_INTENT
            cached["llm_calls"] = 0
            return cached
            
        return None
    
    def _check_simple_crud(self, message: str) -> Optional[Dict[str, Any]]:
        """Pattern matching for simple CRUD operations"""
        message_lower = message.lower()
        
        for intent, patterns in self.simple_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    result = {
                        "intent": intent,
                        "confidence": 0.95,
                        "exit_gate": ExitGate.SIMPLE_CRUD,
                        "llm_calls": 0
                    }
                    
                    # Add specific actions
                    if intent == "inventory_add":
                        # Extract quantity and item
                        qty_match = re.search(r"add (\d+)", message_lower)
                        if qty_match:
                            result["quantity"] = int(qty_match.group(1))
                            result["action"] = "add_item"
                    elif intent == "inventory_list":
                        result["action"] = "list_inventory"
                    elif intent == "inventory_check":
                        result["action"] = "check_item"
                        
                    return result
                    
        return None
    
    def cache_intent(self, message: str, intent: str, confidence: float):
        """Cache successful intent classification"""
        message_hash = hashlib.md5(message.lower().encode()).hexdigest()
        self.intent_cache[message_hash] = {
            "intent": intent,
            "confidence": confidence,
            "cached": True
        }
    
    def should_skip_validation(self, confidence: float, data_type: str) -> bool:
        """Decide if validation LLM can be skipped"""
        
        # High confidence + structured data = skip validation
        if confidence > 0.9 and data_type in ["inventory_crud", "simple_query"]:
            return True
            
        # Known safe operations
        safe_operations = ["list", "get", "check"]
        if any(op in data_type.lower() for op in safe_operations):
            return True
            
        return False
    
    def get_minimal_model_for_task(self, task_type: str) -> str:
        """Return cheapest model that can handle the task"""
        
        model_hierarchy = {
            "intent_classification": "qwen-2.5-7b-instruct",  # Cheapest
            "simple_response": "qwen-2.5-7b-instruct",
            "planning": "qwen-2.5-14b-instruct",  # Medium
            "complex_reasoning": "qwen-2.5-14b-instruct",  # Most expensive
        }
        
        return model_hierarchy.get(task_type, "qwen-2.5-7b-instruct")
    
    def _check_semantic_similarity(self, message: str) -> Optional[Dict[str, Any]]:
        """Fuzzy matching for random queries"""
        message_lower = message.lower()
        
        # Common intent keywords with fuzzy matching
        intent_keywords = {
            "inventory_add": ["add", "put", "store", "insert", "include"],
            "inventory_list": ["show", "list", "display", "view", "see"],
            "inventory_check": ["have", "check", "find", "search", "look"],
            "shopping_list": ["shopping", "buy", "purchase", "need", "list"],
            "recipe": ["cook", "make", "recipe", "prepare", "dish"],
            "help": ["help", "assist", "guide", "support"]
        }
        
        best_match = None
        best_score = 0.0
        
        for intent, keywords in intent_keywords.items():
            for keyword in keywords:
                # Check if keyword appears in message
                if keyword in message_lower:
                    score = 0.8
                else:
                    # Fuzzy matching for typos
                    for word in message_lower.split():
                        similarity = SequenceMatcher(None, keyword, word).ratio()
                        if similarity > 0.7:  # 70% similarity threshold
                            score = similarity
                            break
                    else:
                        continue
                
                if score > best_score:
                    best_score = score
                    best_match = intent
        
        if best_match and best_score > 0.7:
            return {
                "intent": best_match,
                "confidence": best_score,
                "exit_gate": ExitGate.DETERMINISTIC,
                "llm_calls": 0,
                "method": "semantic_similarity"
            }
            
        return None