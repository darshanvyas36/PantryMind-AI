# app/core/agents/complete_agent.py
from typing import Dict, Any, List, Optional
from ..services.java_service_bridge import JavaServiceBridge
from ..llm.groq_client import GroqRecipeClient
from ..memory.memory_manager import MemoryManager
import json
import logging
import re

logger = logging.getLogger(__name__)

class CompleteAgenticAgent:
    """Complete agentic agent with access to ALL PantryMind functionality"""
    
    def __init__(self):
        self.service_bridge = JavaServiceBridge()
        self.llm_client = GroqRecipeClient()
        self.memory = MemoryManager()
        
    async def process_request(self, user_message: str, kitchen_id: int, user_email: str) -> Dict[str, Any]:
        """Process user request with complete PantryMind access"""
        
        logger.info(f"Processing request: {user_message} for kitchen {kitchen_id}")
        
        # Create session ID
        session_id = f"{user_email}_{kitchen_id}"
        
        # Analyze intent and extract parameters
        intent_analysis = await self._analyze_intent(user_message)
        logger.info(f"Intent analysis: {intent_analysis}")
        
        # Execute the appropriate action
        result = await self._execute_action(intent_analysis, kitchen_id, user_email)
        logger.info(f"Action result: {result}")
        
        # Generate response
        response = await self._generate_response(user_message, result)
        logger.info(f"Generated response: {response}")
        
        # Add to memory
        self.memory.add_interaction(session_id, user_message, response, {"action": intent_analysis.get("action")})
        
        return {
            "response": response,
            "action_taken": intent_analysis.get("action"),
            "result": result
        }
    
    async def _analyze_intent(self, user_message: str) -> Dict[str, Any]:
        """Analyze user intent and extract parameters"""
        
        message_lower = user_message.lower()
        
        # Search inventory (specific categories or items)
        search_terms = ['snacks', 'dairy', 'vegetables', 'fruits', 'grains', 'meat', 'beverages', 'condiments', 'spices']
        for term in search_terms:
            if term in message_lower:
                return {"action": "search_inventory", "parameters": {"query": term}}
        
        # Search for specific items
        if any(word in message_lower for word in ['find', 'search', 'look for', 'do i have']):
            # Extract search query
            words = user_message.split()
            query = ""
            for word in words:
                if word.lower() not in ['find', 'search', 'look', 'for', 'do', 'i', 'have', 'any']:
                    query += word + " "
            return {"action": "search_inventory", "parameters": {"query": query.strip()}}
        
        # Show inventory (brief)
        if any(word in message_lower for word in ['show', 'display', 'list', 'view', 'my inventory', 'what do i have']):
            return {"action": "get_inventory", "parameters": {}}
        
        # Add inventory
        if any(word in message_lower for word in ['add', 'put', 'store', 'include']):
            words = user_message.split()
            name = "Unknown Item"
            quantity = 1
            
            if 'add' in message_lower:
                add_index = next(i for i, word in enumerate(words) if word.lower() == 'add')
                if add_index + 1 < len(words):
                    name_words = []
                    for i in range(add_index + 1, min(add_index + 4, len(words))):
                        word = words[i]
                        if word.lower() in ['to', 'in', 'into', 'inventory']:
                            break
                        name_words.append(word)
                    if name_words:
                        name = ' '.join(name_words)
            
            qty_match = re.search(r'(\d+)', user_message)
            if qty_match:
                quantity = int(qty_match.group(1))
            
            return {
                "action": "add_inventory", 
                "parameters": {
                    "name": name,
                    "quantity": quantity,
                    "category_id": 1,
                    "unit_id": 1
                }
            }
        
        # Generate recipes
        if any(word in message_lower for word in ['recipe', 'cook', 'make', 'prepare', 'dish']):
            return {"action": "generate_recipes", "parameters": {}}
        
        # Low stock items
        if any(word in message_lower for word in ['low stock', 'running low', 'need to buy', 'almost empty']):
            return {"action": "get_low_stock", "parameters": {}}
        
        # Shopping list
        if any(word in message_lower for word in ['shopping', 'buy', 'purchase', 'need to get', 'shopping list']):
            return {"action": "get_shopping_lists", "parameters": {}}
        
        # Expiring items
        if any(word in message_lower for word in ['expir', 'expire', 'old', 'spoil']):
            return {"action": "get_expiring_items", "parameters": {}}
        
        # Default to search if no clear intent
        return {"action": "search_inventory", "parameters": {"query": user_message}}
    
    async def _execute_action(self, intent: Dict[str, Any], kitchen_id: int, user_email: str) -> Dict[str, Any]:
        """Execute the determined action"""
        
        action = intent.get("action", "get_inventory")
        params = intent.get("parameters", {})
        
        try:
            if action == "get_inventory":
                return await self.service_bridge.get_inventory_by_kitchen(kitchen_id)
            
            elif action == "add_inventory":
                return await self.service_bridge.add_inventory_manual(
                    kitchen_id=kitchen_id,
                    name=params.get("name", "Unknown Item"),
                    quantity=params.get("quantity", 1),
                    category_id=params.get("category_id", 1),
                    unit_id=params.get("unit_id", 1),
                    user_id=1,
                    description=params.get("description"),
                    location_id=params.get("location_id"),
                    expiry_date=params.get("expiry_date"),
                    price=params.get("price")
                )
            
            elif action == "update_inventory":
                return await self.service_bridge.update_inventory_item(
                    item_id=params.get("item_id"),
                    quantity=params.get("quantity", 1)
                )
            
            elif action == "delete_inventory":
                return await self.service_bridge.delete_inventory_item(params.get("item_id"))
            
            elif action == "get_shopping_lists":
                return await self.service_bridge.get_shopping_lists(kitchen_id)
            
            elif action == "add_to_shopping_list":
                return await self.service_bridge.add_to_shopping_list(
                    kitchen_id=kitchen_id,
                    name=params.get("name", "Unknown Item"),
                    quantity=params.get("quantity", 1),
                    unit_id=params.get("unit_id", 1),
                    category_id=params.get("category_id", 1)
                )
            
            elif action == "remove_shopping_item":
                return await self.service_bridge.remove_shopping_item(params.get("item_id"))
            
            elif action == "update_shopping_item":
                return await self.service_bridge.update_shopping_item(
                    item_id=params.get("item_id"),
                    quantity=params.get("quantity", 1)
                )
            
            elif action == "generate_recipes":
                return await self.service_bridge.generate_recipes(
                    kitchen_id=kitchen_id,
                    servings=params.get("servings", 4),
                    category=params.get("category")
                )
            
            elif action == "get_quick_recipes":
                return await self.service_bridge.get_quick_recipes(
                    kitchen_id=kitchen_id,
                    max_time=params.get("max_time", 30),
                    servings=params.get("servings", 4),
                    user_id=1
                )
            
            elif action == "get_expiring_recipes":
                return await self.service_bridge.get_expiring_recipes(
                    kitchen_id=kitchen_id,
                    servings=params.get("servings", 4),
                    user_id=1
                )
            
            elif action == "get_dashboard_stats":
                return await self.service_bridge.get_dashboard_stats(user_email)
            
            elif action == "get_financial_summary":
                return await self.service_bridge.get_financial_summary(user_email)
            
            elif action == "get_category_breakdown":
                return await self.service_bridge.get_category_breakdown(user_email)
            
            elif action == "get_waste_streak":
                return await self.service_bridge.get_waste_streak(user_email)
            
            elif action == "get_kitchen_members":
                return await self.service_bridge.get_kitchen_members(kitchen_id)
            
            elif action == "get_kitchen_details":
                return await self.service_bridge.get_kitchen_details(kitchen_id)
            
            elif action == "update_member_role":
                return await self.service_bridge.update_member_role(
                    kitchen_id=kitchen_id,
                    member_id=params.get("member_id"),
                    role=params.get("role", "MEMBER")
                )
            
            elif action == "remove_member":
                return await self.service_bridge.remove_kitchen_member(
                    kitchen_id=kitchen_id,
                    member_id=params.get("member_id")
                )
            
            elif action == "generate_invite_code":
                return await self.service_bridge.generate_invite_code(kitchen_id)
            
            elif action == "get_categories":
                return await self.service_bridge.get_categories()
            
            elif action == "get_units":
                return await self.service_bridge.get_units()
            
            elif action == "create_category":
                return await self.service_bridge.create_category(
                    name=params.get("name", "New Category"),
                    description=params.get("description", "")
                )
            
            elif action == "create_unit":
                return await self.service_bridge.create_unit(
                    name=params.get("name", "New Unit"),
                    abbreviation=params.get("abbreviation", "")
                )
            
            elif action == "get_user_profile":
                return await self.service_bridge.get_user_profile(user_email)
            
            elif action == "search_inventory":
                query = params.get("query", "")
                all_inventory = await self.service_bridge.get_inventory_by_kitchen(kitchen_id)
                
                # Filter inventory based on query
                if query:
                    filtered_items = []
                    query_lower = query.lower()
                    for item in all_inventory:
                        if (query_lower in item.get('name', '').lower() or 
                            query_lower in item.get('categoryName', '').lower()):
                            filtered_items.append(item)
                    return filtered_items
                return all_inventory
            
            elif action == "get_expiring_items":
                return await self.service_bridge.get_expiring_items(kitchen_id)
            
            elif action == "get_low_stock":
                low_stock = await self.service_bridge.get_low_stock_items(kitchen_id)
                if not low_stock:
                    return [{"message": "All items are well stocked! No low stock items found."}]
                return low_stock
            
            elif action == "get_expired_items":
                return await self.service_bridge.get_expired_items(kitchen_id)
            
            else:
                return {"error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"Action execution failed: {str(e)}")
            return {"error": str(e)}
    
    async def _generate_response(self, user_message: str, result: Dict[str, Any]) -> str:
        """Generate natural language response"""
        
        # Handle different types of responses
        if "error" in result:
            return f"Sorry, I encountered an error: {result['error']}"
        
        # Handle empty results with message
        if isinstance(result, list) and len(result) == 1 and "message" in result[0]:
            return result[0]["message"]
        
        # Format inventory display
        if isinstance(result, list) and len(result) > 0 and "name" in result[0]:
            return self._format_inventory_response(result)
        
        # Format shopping lists
        if isinstance(result, list) and len(result) > 0 and "listName" in result[0]:
            return self._format_shopping_list_response(result)
        
        # Format other responses
        if "success" in result or "message" in result:
            return result.get("message", "Operation completed successfully!")
        
        # Use LLM for complex responses
        system_prompt = """You are PantryMind AI assistant. Generate a helpful, natural response based on the user's request and the action result.

Be conversational, helpful, and specific. If there's an error, explain it clearly. If successful, summarize what was done and provide relevant details.

Keep responses concise but informative."""

        context = f"User asked: {user_message}\nAction result: {json.dumps(result, indent=2)}"
        
        try:
            prompt = f"{system_prompt}\n\n{context}\n\nResponse:"
            response = await self.llm_client.text_completion(
                prompt=prompt,
                max_tokens=300,
                temperature=0.7
            )
            return response
        except Exception as e:
            return "Operation completed successfully!"
    
    def _format_inventory_response(self, inventory_items: List[Dict[str, Any]]) -> str:
        """Format inventory items into readable response"""
        
        if not inventory_items:
            return "No items found. You can add items by saying 'add [item name] to inventory'."
        
        # Check if this is a search result (fewer items)
        is_search = len(inventory_items) < 10
        
        if is_search:
            response = f"Found {len(inventory_items)} item(s):\n\n"
            for item in inventory_items:
                name = item.get('name', 'Unknown')
                quantity = item.get('totalQuantity', 0)
                unit = item.get('unitName', '')
                category = item.get('categoryName', '')
                response += f"• {name}: {quantity} {unit} ({category})\n"
        else:
            # Group by category for full inventory
            categories = {}
            for item in inventory_items:
                cat_name = item.get('categoryName', 'Other')
                if cat_name not in categories:
                    categories[cat_name] = []
                categories[cat_name].append(item)
            
            response = f"Your inventory ({len(inventory_items)} items):\n\n"
            for category, items in categories.items():
                response += f"**{category}** ({len(items)} items)\n"
                # Show only first 3 items per category to keep it concise
                for i, item in enumerate(items[:3]):
                    name = item.get('name', 'Unknown')
                    quantity = item.get('totalQuantity', 0)
                    unit = item.get('unitName', '')
                    response += f"  • {name}: {quantity} {unit}\n"
                if len(items) > 3:
                    response += f"  ... and {len(items) - 3} more\n"
                response += "\n"
        
        response += "\nAsk me to 'find snacks' or 'add apples' or 'generate recipes'!"
        return response
    
    def _format_shopping_list_response(self, shopping_lists: List[Dict[str, Any]]) -> str:
        """Format shopping lists into readable response"""
        
        if not shopping_lists:
            return "No shopping lists found. Low stock items will be automatically added to your shopping list."
        
        response = "Your Shopping Lists:\n\n"
        
        for shopping_list in shopping_lists:
            list_name = shopping_list.get('listName', 'Shopping List')
            items = shopping_list.get('items', [])
            
            response += f"**{list_name}** ({len(items)} items)\n"
            
            if not items:
                response += "  No items yet\n"
            else:
                for item in items[:5]:  # Show first 5 items
                    name = item.get('name', 'Unknown')
                    quantity = item.get('quantity', 1)
                    unit = item.get('unitName', '')
                    response += f"  • {name}: {quantity} {unit}\n"
                
                if len(items) > 5:
                    response += f"  ... and {len(items) - 5} more items\n"
            
            response += "\n"
        
        response += "Say 'add [item] to shopping list' to add more items!"
        return response