# app/agents/llm_intent_agent.py
from typing import Dict, Any
from .base import BaseAgent, AgentResult
import requests
import json

class LLMIntentAgent(BaseAgent):
    def __init__(self, model_name: str = "amazon/nova-2-lite-v1:free"):
        super().__init__("LLMIntentAgent", model_name)
        
    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        message = input_data.get("message", "")
        
        # Create prompt for intent classification
        prompt = f"""Classify the user's intent for a pantry management system. 

User message: "{message}"

Available intents:
- inventory_list: Show all inventory items
- inventory_category: Show items from specific category (vegetables, fruits, dairy, etc.)
- inventory_add: Add new items to inventory
- inventory_consume: Remove/consume items from inventory
- inventory_check: Check specific items
- shopping_list: Show or manage shopping list
- recipe: Find recipes or cooking suggestions
- greeting: Hello, hi, hey
- help: Help or guidance requests

Respond with ONLY a JSON object:
{{"intent": "intent_name", "confidence": 0.9, "category": "category_name_if_applicable"}}

Examples:
- "show vegetables" -> {{"intent": "inventory_category", "confidence": 0.9, "category": "vegetables"}}
- "vegetables i have" -> {{"intent": "inventory_category", "confidence": 0.9, "category": "vegetables"}}
- "consume 200g rice" -> {{"intent": "inventory_consume", "confidence": 0.9}}
- "show inventory" -> {{"intent": "inventory_list", "confidence": 0.9}}
- "hello" -> {{"intent": "greeting", "confidence": 1.0}}"""

        try:
            # Call OpenRouter API
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._get_api_key()}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 100
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                print(f"DEBUG: LLM Response: {content}")
                
                # Parse JSON response
                try:
                    intent_data = json.loads(content)
                    intent = intent_data.get("intent", "help")
                    confidence = intent_data.get("confidence", 0.5)
                    category = intent_data.get("category")
                    
                    print(f"DEBUG: Parsed intent: {intent}, confidence: {confidence}")
                    
                    return AgentResult(
                        success=True,
                        data={
                            "intent": intent,
                            "confidence": confidence,
                            "category": category
                        },
                        confidence=confidence,
                        metadata={"classification": "llm_based"}
                    )
                    
                except json.JSONDecodeError as e:
                    print(f"DEBUG: JSON parse error: {e}, content: {content}")
                    # Fallback parsing
                    if "inventory_category" in content:
                        return AgentResult(
                            success=True,
                            data={"intent": "inventory_category", "confidence": 0.8},
                            confidence=0.8,
                            metadata={"classification": "llm_fallback"}
                        )
                    elif "inventory_list" in content:
                        return AgentResult(
                            success=True,
                            data={"intent": "inventory_list", "confidence": 0.8},
                            confidence=0.8,
                            metadata={"classification": "llm_fallback"}
                        )
            else:
                print(f"DEBUG: OpenRouter API error: {response.status_code}")
                print(f"DEBUG: Response text: {response.text[:200]}")
                print(f"DEBUG: Using model: {self.model_name}")
                print(f"DEBUG: API key exists: {bool(api_key)}")
            
        except Exception as e:
            print(f"DEBUG: LLM Intent classification error: {e}")
            print(f"DEBUG: Model: {self.model_name}, API key exists: {bool(self._get_openrouter_api_key())}")
        
        # Final fallback to rule-based
        print(f"DEBUG: Falling back to rule-based classification")
        return self._rule_based_fallback(message)
    
    def _rule_based_fallback(self, message: str) -> AgentResult:
        """Fallback to simple rules if LLM fails"""
        print(f"DEBUG: Using rule-based fallback for: {message}")
        message_lower = message.lower().strip()
        
        # Flexible greeting detection
        greeting_words = ["hello", "hi", "hey", "hii", "helo", "hai"]
        if any(word in message_lower for word in greeting_words) or message_lower in greeting_words:
            return AgentResult(
                success=True,
                data={"intent": "greeting", "confidence": 0.9},
                confidence=0.9,
                metadata={"classification": "rule_fallback"}
            )
        
        if any(word in message_lower for word in ["inventory", "stock", "items", "show", "list"]):
            return AgentResult(
                success=True,
                data={"intent": "inventory_list", "confidence": 0.8},
                confidence=0.8,
                metadata={"classification": "rule_fallback"}
            )
        
        return AgentResult(
            success=True,
            data={"intent": "help", "confidence": 0.3},
            confidence=0.3,
            metadata={"classification": "rule_fallback"}
        )
    
    def _get_api_key(self) -> str:
        """Get OpenRouter API key from settings"""
        from ..config.settings import settings
        return settings.openrouter_api_key or ""