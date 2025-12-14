# app/agents/smart_pantry_agent.py
from typing import Dict, Any
import requests
import json
from .gemini_agent import GeminiAgent

class SmartPantryAgent:
    def __init__(self, java_backend_url: str = "http://localhost:8080"):
        self.gemini = GeminiAgent()
        self.java_backend_url = java_backend_url
        self.chat_history = {}  # Store by user_email
        
    def process_message(self, message: str, kitchen_id: int, user_email: str) -> str:
        """Process user message with full LLM intelligence"""
        
        # Get current inventory data
        inventory_data = self._get_inventory_data(kitchen_id)
        
        # Create comprehensive system prompt
        system_prompt = f"""You are PantryMind, an intelligent pantry management assistant. 

Current inventory data (showing all {len(inventory_data)} items):
{json.dumps(inventory_data, indent=2) if inventory_data else "No inventory data available"}

You can help users with:
1. Show inventory (all items, by category, specific items)
2. Add/remove items from inventory  
3. Check expiring items
4. Generate recipes based on available ingredients
5. Manage shopping lists
6. Provide cooking suggestions

Guidelines:
- Be conversational and helpful
- Use the actual inventory data in your responses
- For greetings, be friendly and offer help
- For inventory queries, show relevant items with quantities and units
- For category queries (fruits, vegetables, etc.), filter by categoryName
- For recipe requests, suggest dishes based on available ingredients
- If you need to perform actions (add/remove items), explain what you would do

Respond naturally and conversationally. Use emojis when appropriate."""

        # Get or create chat history for this user
        if user_email not in self.chat_history:
            self.chat_history[user_email] = []
        
        history = self.chat_history[user_email]
        
        # Add recent conversation context
        recent_history = "\n".join([f"User: {h['user']}\nAssistant: {h['assistant']}" for h in history[-3:]])
        
        if recent_history:
            system_prompt += f"\n\nRecent conversation:\n{recent_history}"
        
        # Get LLM response
        response = self.gemini.chat(system_prompt, message)
        
        if not response:
            return "I'm having trouble right now. Please try again in a moment."
        
        # Store in chat history
        self.chat_history[user_email].append({
            "user": message,
            "assistant": response
        })
        
        # Keep only last 10 exchanges
        if len(self.chat_history[user_email]) > 10:
            self.chat_history[user_email] = self.chat_history[user_email][-10:]
            
        return response
    
    def _get_inventory_data(self, kitchen_id: int) -> list:
        """Fetch current inventory data from Java backend"""
        
        try:
            response = requests.post(
                f"{self.java_backend_url}/api/internal/inventory/getAll",
                json={"kitchenId": kitchen_id},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch inventory: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Inventory fetch error: {e}")
            return []
    
    def _add_inventory_item(self, name: str, quantity: float, unit: str, category: str, kitchen_id: int) -> bool:
        """Add item to inventory via Java backend"""
        try:
            response = requests.post(
                f"{self.java_backend_url}/api/internal/inventory/add",
                json={
                    "kitchenId": kitchen_id,
                    "name": name,
                    "quantity": quantity,
                    "unit": unit,
                    "category": category
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Add inventory error: {e}")
            return False