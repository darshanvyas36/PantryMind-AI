# app/agents/optimized_state_machine.py
from typing import Dict, Any, Optional
from .cost_optimizer import CostOptimizer, ExitGate
from .state_machine import AgentStateMachine
from .governor import AgentRole
import requests

class OptimizedStateMachine(AgentStateMachine):
    def __init__(self, java_backend_url: str = "http://localhost:8080"):
        super().__init__(java_backend_url)
        self.java_backend_url = java_backend_url  # Store for direct access
        self.cost_optimizer = CostOptimizer()
        self.request_stats = {"llm_calls": 0, "early_exits": 0, "java_direct": 0}
        
    def process_message(self, message: str, kitchen_id: int, user_email: str) -> str:
        """Cost-optimized message processing with early exits"""
        
        # Only allow exact greetings to exit early
        if message.lower().strip() in ["hello", "hi", "hey"]:
            self.request_stats["early_exits"] += 1
            return "Hello! 👋 I'm your PantryMind assistant. What can I help you with?"
        
        # Route everything else through LLM for better understanding
        self.request_stats["llm_calls"] += 1
        return self._process_with_minimal_llm(message, kitchen_id, user_email)
    
    def _handle_early_exit(self, result: Dict[str, Any], kitchen_id: int, user_email: str) -> str:
        """Handle requests that can exit early"""
        
        # Direct response available
        if "response" in result:
            return result["response"]
        
        # Direct action needed
        if "action" in result:
            action = result["action"]
            
            if action == "list_inventory":
                return self._get_inventory_direct(kitchen_id)
            elif action == "add_item":
                return f"I can help you add items. Please specify what you'd like to add."
            elif action == "check_item":
                return f"What item would you like me to check in your inventory?"
        
        # Handle specific inventory intents
        intent = result.get("intent")
        if intent == "inventory_expiring":
            return self._get_expiring_items(kitchen_id)
        elif intent == "inventory_low_stock":
            return self._get_low_stock_items(kitchen_id)
        elif intent == "inventory_list":
            return self._get_inventory_direct(kitchen_id)
        
        return "How can I help you today?"
    
    def _should_route_to_java(self, message: str) -> bool:
        """Determine if Java backend should handle directly"""
        
        java_keywords = [
            "get inventory", "list all", "show stats", "dashboard",
            "count items", "total value", "categories", "what inventory"
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in java_keywords)
    
    def _route_to_java_backend(self, message: str, kitchen_id: int, user_email: str) -> str:
        """Route simple queries directly to Java backend"""
        
        try:
            # Map message to Java API endpoint
            if any(word in message.lower() for word in ["inventory", "list", "show"]):
                response = requests.post(
                    f"{self.java_backend_url}/api/internal/inventory/getAll",
                    json={"kitchenId": kitchen_id}
                )
                
                if response.status_code == 200:
                    inventory = response.json()
                    print(f"DEBUG: Java direct route - found {len(inventory)} items")
                    return f"Found {len(inventory)} items in your pantry."
                    
            elif "stats" in message.lower() or "dashboard" in message.lower():
                response = requests.post(
                    f"{self.java_backend_url}/api/internal/dashboard/stats",
                    json={"kitchenId": kitchen_id}
                )
                
                if response.status_code == 200:
                    stats = response.json()
                    return f"Pantry stats: {stats.get('totalItems', 0)} items, {stats.get('expiringItems', 0)} expiring soon."
                    
        except Exception as e:
            print(f"Java backend error: {e}")
            
        return "I'll help you with that request."
    
    def _get_inventory_direct(self, kitchen_id: int) -> str:
        """Get inventory without LLM processing"""
        
        try:
            response = requests.post(
                f"{self.java_backend_url}/api/internal/inventory/getAll",
                json={"kitchenId": kitchen_id}
            )
            
            if response.status_code == 200:
                inventory = response.json()
                print(f"DEBUG: Raw inventory data: {inventory[:3] if inventory else 'Empty'}")
                
                if not inventory:
                    return "Your pantry is empty. Start by adding some items!"
                
                # Debug: Show sample items
                for i, item in enumerate(inventory[:3]):
                    print(f"DEBUG: Item {i}: name={item.get('name')}, totalQuantity={item.get('totalQuantity')}, unitName={item.get('unitName')}")
                
                # Filter out items with zero quantity - use totalQuantity
                non_zero_items = [item for item in inventory if item.get('totalQuantity', 0) > 0]
                print(f"DEBUG: Total items: {len(inventory)}, Non-zero items: {len(non_zero_items)}")
                
                if not non_zero_items:
                    return "Your pantry appears to be empty or all items are out of stock. Time to go shopping! 🛒"
                
                response_text = f"You have {len(non_zero_items)} items in stock:\n\n"
                for item in non_zero_items[:10]:  # Show first 10 non-zero items
                    name = item.get('name', 'Unknown')
                    quantity = item.get('totalQuantity', 0)
                    unit = item.get('unitName', '')
                    response_text += f"• {name} - {quantity} {unit}\n"
                
                if len(non_zero_items) > 10:
                    response_text += f"\n... and {len(non_zero_items) - 10} more items in stock."
                
                # Show summary of zero items if any
                zero_items = len(inventory) - len(non_zero_items)
                if zero_items > 0:
                    response_text += f"\n\n⚠️ {zero_items} items are out of stock."
                    
                return response_text
                
        except Exception as e:
            print(f"DEBUG: Direct inventory fetch error: {e}")
            print(f"DEBUG: Java backend URL: {self.java_backend_url}")
            
        return "I couldn't fetch your inventory right now. Please try again."
    
    def _get_expiring_items(self, kitchen_id: int) -> str:
        """Get items expiring soon without LLM processing"""
        
        try:
            response = requests.post(
                f"{self.java_backend_url}/api/internal/inventory/getExpiring",
                json={"kitchenId": kitchen_id}
            )
            
            if response.status_code == 200:
                expiring_items = response.json()
                if not expiring_items:
                    return "Great news! No items are expiring soon in your pantry."
                
                response_text = f"⚠️ You have {len(expiring_items)} items expiring soon:\n\n"
                for item in expiring_items[:10]:
                    name = item.get('name', 'Unknown')
                    expiry_date = item.get('expiryDate', 'Unknown')
                    response_text += f"• {name} - expires {expiry_date}\n"
                
                return response_text
                
        except Exception as e:
            print(f"Expiring items fetch error: {e}")
            
        return "I couldn't check expiring items right now. Please try again."
    
    def _get_low_stock_items(self, kitchen_id: int) -> str:
        """Get low stock items without LLM processing"""
        
        try:
            # Mock low stock check - in real implementation, this would be a proper API
            response = requests.post(
                f"{self.java_backend_url}/api/internal/inventory/getAll",
                json={"kitchenId": kitchen_id}
            )
            
            if response.status_code == 200:
                all_items = response.json()
                # Filter items with quantity <= 2 as low stock
                low_stock = [item for item in all_items if item.get('quantity', 0) <= 2]
                
                if not low_stock:
                    return "All items are well stocked! 📦"
                
                response_text = f"📉 You have {len(low_stock)} items running low:\n\n"
                for item in low_stock[:10]:
                    name = item.get('name', 'Unknown')
                    quantity = item.get('quantity', 0)
                    unit = item.get('unit', '')
                    response_text += f"• {name} - only {quantity} {unit} left\n"
                
                return response_text
                
        except Exception as e:
            print(f"Low stock fetch error: {e}")
            
        return "I couldn't check low stock items right now. Please try again."
    
    def _get_shopping_list(self, kitchen_id: int) -> str:
        """Get shopping list without LLM processing"""
        
        try:
            response = requests.post(
                f"{self.java_backend_url}/api/internal/shopping/getLists",
                json={"kitchenId": kitchen_id}
            )
            
            if response.status_code == 200:
                shopping_lists = response.json()
                if not shopping_lists:
                    return "Your shopping list is empty. Add items you need to buy!"
                
                response_text = f"🛒 Your shopping list ({len(shopping_lists)} items):\n\n"
                for item in shopping_lists[:10]:
                    name = item.get('itemName', 'Unknown')
                    quantity = item.get('quantity', 1)
                    response_text += f"• {name} - {quantity}\n"
                
                return response_text
                
        except Exception as e:
            print(f"Shopping list fetch error: {e}")
            
        return "I couldn't fetch your shopping list right now. Please try again."
    
    def _get_inventory_by_category(self, message: str, kitchen_id: int, category_hint: str = None) -> str:
        """Get inventory filtered by category"""
        
        try:
            response = requests.post(
                f"{self.java_backend_url}/api/internal/inventory/getAll",
                json={"kitchenId": kitchen_id}
            )
            
            if response.status_code == 200:
                inventory = response.json()
                
                # Use category hint from LLM or extract from message
                target_category = None
                if category_hint:
                    category_map = {
                        "vegetables": "Vegetables",
                        "fruits": "Fruits", 
                        "dairy": "Dairy",
                        "meat": "Meat",
                        "grains": "Grains"
                    }
                    target_category = category_map.get(category_hint.lower())
                
                if not target_category:
                    # Fallback to message parsing
                    message_lower = message.lower()
                    category_map = {
                        "vegetables": "Vegetables",
                        "fruits": "Fruits", 
                        "dairy": "Dairy",
                        "meat": "Meat",
                        "grains": "Grains"
                    }
                    
                    for key, value in category_map.items():
                        if key in message_lower:
                            target_category = value
                            break
                
                if target_category:
                    filtered_items = [item for item in inventory if item.get('categoryName') == target_category and item.get('totalQuantity', 0) > 0]
                else:
                    filtered_items = [item for item in inventory if item.get('totalQuantity', 0) > 0]
                
                if not filtered_items:
                    return f"No {target_category.lower() if target_category else 'items'} found in your pantry."
                
                response_text = f"You have {len(filtered_items)} {target_category.lower() if target_category else 'items'} in stock:\n\n"
                for item in filtered_items[:10]:
                    name = item.get('name', 'Unknown')
                    quantity = item.get('totalQuantity', 0)
                    unit = item.get('unitName', '')
                    response_text += f"• {name} - {quantity} {unit}\n"
                
                return response_text
                
        except Exception as e:
            print(f"Category inventory fetch error: {e}")
            
        return "I couldn't fetch the category inventory right now. Please try again."
    
    def _process_with_minimal_llm(self, message: str, kitchen_id: int, user_email: str) -> str:
        """Process with minimal LLM usage"""
        
        # Use only intent agent for classification
        intent_agent = self.agents[AgentRole.INTENT]
        intent_result = intent_agent.execute({"message": message})
        
        if not intent_result.success:
            return "I'm having trouble understanding your request. Could you rephrase it?"
        
        intent = intent_result.data.get("intent")
        confidence = intent_result.data.get("confidence", 0.0)
        
        print(f"DEBUG: Intent result - intent: {intent}, confidence: {confidence}, success: {intent_result.success}")
        
        # If no intent detected, return error message
        if not intent:
            return "I'm not sure what you're asking for. Could you please rephrase your request?"
        
        # Cache successful intent
        self.cost_optimizer.cache_intent(message, intent, confidence)
        
        # Execute direct action for any valid intent
        if confidence > 0.5:
            return self._execute_direct_action(intent, message, kitchen_id, user_email)
        
        # Low confidence = fall back to full pipeline
        return super().process_message(message, kitchen_id, user_email)
    
    def _execute_direct_action(self, intent: str, message: str, kitchen_id: int, user_email: str) -> str:
        """Execute action directly without planning"""
        
        if intent in ["inventory", "inventory_list", "inventory_check"]:
            return self._get_inventory_direct(kitchen_id)
        elif intent == "inventory_category":
            # Get category from intent result if available
            category = None
            if hasattr(intent_result, 'data') and intent_result.data:
                category = intent_result.data.get('category')
            return self._get_inventory_by_category(message, kitchen_id, category)
        elif intent == "inventory_consume":
            return "I can help you update inventory after consumption. Please specify the item and quantity consumed (e.g., 'consumed 200g rice')."
        elif intent == "inventory_expiring":
            return self._get_expiring_items(kitchen_id)
        elif intent == "inventory_low_stock":
            return self._get_low_stock_items(kitchen_id)
        elif intent == "shopping_list":
            return self._get_shopping_list(kitchen_id)
        elif intent == "inventory_add":
            return "I can help you add items to your inventory. Please specify the item name, quantity, and unit (e.g., '2 kg tomatoes')."
        elif intent == "greeting":
            return "Hello! 👋 I'm your PantryMind assistant. What can I help you with today?"
        elif intent == "help":
            return """I can help you with:
• Check inventory - "show my items"
• Add items - "add 2 milk"  
• Find recipes - "what can I cook?"
• Process receipts - "scan my receipt"
• View stats - "show pantry stats" """
        elif intent == "recipe":
            # Only for recipe, we need the full pipeline
            return super().process_message(message, kitchen_id, user_email)
        else:
            return "I can help you with that. Could you be more specific?"
    
    def get_cost_stats(self) -> Dict[str, Any]:
        """Return cost optimization statistics"""
        total_requests = sum(self.request_stats.values())
        
        return {
            "total_requests": total_requests,
            "early_exits": self.request_stats["early_exits"],
            "java_direct": self.request_stats["java_direct"], 
            "llm_calls": self.request_stats["llm_calls"],
            "cost_savings": f"{((self.request_stats['early_exits'] + self.request_stats['java_direct']) / max(total_requests, 1)) * 100:.1f}%"
        }