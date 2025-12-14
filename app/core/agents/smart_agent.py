# app/core/agents/smart_agent.py
from typing import Dict, Any, List, Optional
from ..services.java_service_bridge import JavaServiceBridge
from ..llm.groq_client import GroqRecipeClient
from ..memory.memory_manager import MemoryManager
import json
import logging

logger = logging.getLogger(__name__)

class SmartAgenticAgent:
    """Smart agent that uses LLM for all intent analysis and response generation"""
    
    def __init__(self):
        self.service_bridge = JavaServiceBridge()
        self.llm_client = GroqRecipeClient()
        self.memory = MemoryManager()
        
    async def process_request(self, user_message: str, kitchen_id: int, user_email: str) -> Dict[str, Any]:
        """Process user request with LLM-driven intent analysis"""
        
        session_id = f"{user_email}_{kitchen_id}"
        
        # Use LLM for intent analysis with full system context
        intent_analysis = await self._analyze_intent_with_llm(user_message)
        
        # Execute action dynamically
        result = await self._execute_action_dynamically(intent_analysis, kitchen_id, user_email)
        
        # Generate response with LLM
        response = await self._generate_response_with_llm(user_message, result)
        
        # Store in memory
        self.memory.add_interaction(session_id, user_message, response, {"action": intent_analysis.get("action")})
        
        return {
            "response": response,
            "action_taken": intent_analysis.get("action"),
            "result": result
        }
    
    async def _analyze_intent_with_llm(self, user_message: str) -> Dict[str, Any]:
        """Use LLM to analyze intent with full system knowledge"""
        
        system_prompt = """You are PantryMind AI assistant. Analyze the user's message and determine the best action.

AVAILABLE ACTIONS & ENDPOINTS:
- get_inventory: Show all inventory items
- search_inventory: Search items by name/category (params: query)
- add_inventory: Add new item (params: name, quantity, category_id, unit_id)
- consume_inventory: Consume/reduce item quantity (params: name, quantity)
- get_low_stock: Items below minimum stock (suggested for shopping)
- get_expiring_items: Items expiring soon
- get_shopping_lists: Show shopping lists and suggested items to buy
- add_to_shopping_list: Add item to shopping (params: name, quantity)
- generate_recipes: Generate recipes from inventory
- get_quick_recipes: Quick recipes under time limit (params: max_time)
- get_expiring_recipes: Recipes using expiring ingredients
- get_recipe_by_name: Specific recipe (params: recipe_name)
- get_dashboard_stats: Dashboard statistics
- get_financial_summary: Financial reports
- get_category_breakdown: Category usage reports
- get_kitchen_members: Kitchen members list
- get_categories: All categories
- get_units: All measurement units
- get_user_profile: User profile info

KEY MAPPINGS:
- "suggested items", "what to buy", "shopping suggestions" → get_shopping_lists
- "low stock", "running low", "need to buy" → get_low_stock
- "my inventory", "what do I have" → get_inventory
- "find [item]", "search [category]" → search_inventory
- "add [quantity] [item]", "put [quantity] [item]" → add_inventory
- "consume [quantity] [item]", "use [quantity] [item]", "drink [quantity]" → consume_inventory

IMPORTANT: "add" means ADD to inventory, "consume/use/drink" means REDUCE from inventory

CATEGORIES: Dairy(1), Vegetables(2), Fruits(3), Meat(4), Grains(5), Beverages(6), Snacks(7), Condiments(10), Spices(9)
UNITS: grams(1), kg(2), ml(3), liter(4), piece(5)

Return JSON: {"action": "action_name", "parameters": {...}}"""

        try:
            response = await self.llm_client.text_completion(
                prompt=f"{system_prompt}\n\nUser: {user_message}\n\nJSON:",
                max_tokens=150,
                temperature=0.1
            )
            return json.loads(response)
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return {"action": "get_inventory", "parameters": {}}
    
    async def _execute_action_dynamically(self, intent: Dict[str, Any], kitchen_id: int, user_email: str) -> Dict[str, Any]:
        """Execute action using dynamic mapping"""
        
        action = intent.get("action", "get_inventory")
        params = intent.get("parameters", {})
        
        # Dynamic action mapping
        action_map = {
            "get_inventory": lambda: self.service_bridge.get_inventory_by_kitchen(kitchen_id),
            "search_inventory": lambda: self._search_inventory(kitchen_id, params.get("query", "")),
            "add_inventory": lambda: self._add_inventory_item(
                kitchen_id, params.get("name", "Unknown"), params.get("quantity", 1)
            ),
            "update_inventory": lambda: self.service_bridge.update_inventory_item(
                params.get("item_id"), params.get("quantity", 1)
            ),
            "consume_inventory": lambda: self._consume_inventory_item(
                kitchen_id, params.get("name", ""), params.get("quantity", 1)
            ),
            "get_low_stock": lambda: self._get_low_stock_with_message(kitchen_id),
            "get_expiring_items": lambda: self.service_bridge.get_expiring_items(kitchen_id),
            "get_expired_items": lambda: self.service_bridge.get_expired_items(kitchen_id),
            "get_shopping_lists": lambda: self._get_shopping_suggestions(kitchen_id),
            "add_to_shopping_list": lambda: self.service_bridge.add_to_shopping_list(
                kitchen_id, params.get("name", "Unknown"), params.get("quantity", 1)
            ),
            "generate_recipes": lambda: self.service_bridge.generate_recipes(
                kitchen_id, params.get("servings", 4), params.get("category")
            ),
            "get_quick_recipes": lambda: self.service_bridge.get_quick_recipes(
                kitchen_id, params.get("max_time", 30), params.get("servings", 4), 1
            ),
            "get_expiring_recipes": lambda: self.service_bridge.get_expiring_recipes(
                kitchen_id, params.get("servings", 4), 1
            ),
            "get_recipe_by_name": lambda: self.service_bridge.get_recipe_by_name(
                kitchen_id, params.get("recipe_name", ""), params.get("servings", 4)
            ),
            "get_dashboard_stats": lambda: self.service_bridge.get_dashboard_stats(user_email),
            "get_financial_summary": lambda: self.service_bridge.get_financial_summary(user_email),
            "get_category_breakdown": lambda: self.service_bridge.get_category_breakdown(user_email),
            "get_kitchen_members": lambda: self.service_bridge.get_kitchen_members(kitchen_id),
            "get_categories": lambda: self.service_bridge.get_categories(),
            "get_units": lambda: self.service_bridge.get_units(),
            "get_user_profile": lambda: self.service_bridge.get_user_profile(user_email),
        }
        
        try:
            if action in action_map:
                return await action_map[action]()
            else:
                return {"error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Action execution failed: {str(e)}")
            return {"error": str(e)}
    
    async def _search_inventory(self, kitchen_id: int, query: str) -> List[Dict[str, Any]]:
        """Search inventory with query"""
        all_inventory = await self.service_bridge.get_inventory_by_kitchen(kitchen_id)
        if not query:
            return all_inventory
        
        query_lower = query.lower()
        return [item for item in all_inventory 
                if query_lower in item.get('name', '').lower() or 
                   query_lower in item.get('categoryName', '').lower()]
    
    async def _get_low_stock_with_message(self, kitchen_id: int) -> List[Dict[str, Any]]:
        """Get low stock items with fallback message"""
        low_stock = await self.service_bridge.get_low_stock_items(kitchen_id)
        if not low_stock:
            return [{"message": "All items are well stocked! No low stock items found."}]
        return low_stock
    
    async def _consume_inventory_item(self, kitchen_id: int, item_name: str, consume_qty: int) -> Dict[str, Any]:
        """Consume/reduce quantity of an inventory item"""
        try:
            all_items = await self.service_bridge.get_inventory_by_kitchen(kitchen_id)
            target_item = None
            
            for item in all_items:
                if item.get('name', '').lower() == item_name.lower():
                    target_item = item
                    break
            
            if not target_item:
                return {"error": f"Item '{item_name}' not found in inventory"}
            
            current_qty = target_item.get('totalQuantity', 0)
            if current_qty < consume_qty:
                return {"error": f"Not enough {item_name}. Available: {current_qty}, Requested: {consume_qty}"}
            
            new_qty = current_qty - consume_qty
            
            items = target_item.get('items', [])
            if items:
                item_id = items[0].get('id')
                await self.service_bridge.update_inventory_item(item_id, new_qty)
                return {
                    "success": True,
                    "message": f"Consumed {consume_qty} of {item_name}. Remaining: {new_qty}"
                }
            else:
                return {"error": f"No items found for {item_name}"}
                
        except Exception as e:
            logger.error(f"Error consuming inventory: {str(e)}")
            return {"error": str(e)}
    
    async def _add_inventory_item(self, kitchen_id: int, item_name: str, add_qty: int) -> Dict[str, Any]:
        """Add quantity to existing item or create new item"""
        try:
            all_items = await self.service_bridge.get_inventory_by_kitchen(kitchen_id)
            target_item = None
            
            for item in all_items:
                if item.get('name', '').lower() == item_name.lower():
                    target_item = item
                    break
            
            if target_item:
                # Update existing item
                current_qty = target_item.get('totalQuantity', 0)
                new_qty = current_qty + add_qty
                
                items = target_item.get('items', [])
                if items:
                    item_id = items[0].get('id')
                    await self.service_bridge.update_inventory_item(item_id, new_qty)
                    return {
                        "success": True,
                        "message": f"Added {add_qty} to {item_name}. Total: {new_qty}"
                    }
            else:
                # Create new item
                result = await self.service_bridge.add_inventory_manual(
                    kitchen_id, item_name, add_qty, 6, 3, 1  # Beverages, ml
                )
                return {
                    "success": True,
                    "message": f"Added new item: {item_name} ({add_qty})"
                }
                
        except Exception as e:
            logger.error(f"Error adding inventory: {str(e)}")
            return {"error": str(e)}
    
    async def _get_shopping_suggestions(self, kitchen_id: int) -> Dict[str, Any]:
        """Get shopping suggestions combining shopping lists and low stock items"""
        shopping_lists = await self.service_bridge.get_shopping_lists(kitchen_id)
        low_stock = await self.service_bridge.get_low_stock_items(kitchen_id)
        
        return {
            "shopping_lists": shopping_lists,
            "low_stock_suggestions": low_stock,
            "type": "shopping_suggestions"
        }
    
    async def _generate_response_with_llm(self, user_message: str, result: Dict[str, Any]) -> str:
        """Generate response using LLM with full context"""
        
        # Handle errors
        if "error" in result:
            return f"Sorry, I encountered an error: {result['error']}"
        
        # Handle simple messages
        if isinstance(result, list) and len(result) == 1 and "message" in result[0]:
            return result[0]["message"]
        
        # Handle success messages
        if isinstance(result, dict) and "success" in result and "message" in result:
            return result["message"]
        
        # Handle shopping suggestions specially
        if isinstance(result, dict) and result.get("type") == "shopping_suggestions":
            return await self._format_shopping_suggestions(result)
        
        # Use LLM for all other responses
        system_prompt = """You are PantryMind AI assistant. Generate helpful, natural responses based on the data provided.

FORMATTING RULES FOR INVENTORY ITEMS:
- Always show: Name, Current Quantity with Unit
- For low stock: Show minimum stock level too
- Format: "• ItemName: CurrentQty Unit (min: MinStock)"
- Group by category when showing multiple items
- Keep it simple and clean
- Only show additional details if user specifically asks

EXAMPLE:
**Fruits:**
• Apples: 2000 grams (expires: Dec 26, 2025)
• Bananas: 12 piece (expires: Dec 17, 2025)

FOR OTHER DATA TYPES:
- Shopping lists: Show items to buy
- Recipes: Show recipe names and key ingredients
- Statistics: Summarize key numbers

Keep responses conversational and helpful. Don't show raw JSON data."""

        # Simplify data for LLM processing
        if isinstance(result, list) and len(result) > 0 and "name" in str(result[0]):
            simplified_data = []
            for item in result[:10]:
                simplified_item = {
                    "name": item.get("name", "Unknown"),
                    "totalQuantity": item.get("totalQuantity", 0),
                    "unitName": item.get("unitName", ""),
                    "categoryName": item.get("categoryName", ""),
                    "minStock": item.get("minStock", 0)
                }
                simplified_data.append(simplified_item)
            data_str = json.dumps(simplified_data, indent=2)
        else:
            data_str = json.dumps(result, indent=2)[:1500]
        
        context = f"User asked: {user_message}\nData: {data_str}"
        
        try:
            response = await self.llm_client.text_completion(
                prompt=f"{system_prompt}\n\n{context}\n\nResponse:",
                max_tokens=400,
                temperature=0.3
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return "Operation completed successfully!"
    
    async def _format_shopping_suggestions(self, data: Dict[str, Any]) -> str:
        """Format shopping suggestions using LLM"""
        
        context = f"Shopping data: {json.dumps(data, indent=2)[:1000]}..."
        
        prompt = """Format this shopping data into a helpful response.

Show:
1. Shopping lists with item names and quantities
2. Low stock items that need to be bought
3. Keep it clean and organized

""" + context + "\n\nResponse:"
        
        try:
            response = await self.llm_client.text_completion(
                prompt=prompt,
                max_tokens=300,
                temperature=0.3
            )
            return response.strip()
        except Exception as e:
            return "Shopping suggestions available. Please try again."