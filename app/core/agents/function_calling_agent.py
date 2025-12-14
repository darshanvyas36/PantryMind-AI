# app/core/agents/function_calling_agent.py
from typing import Dict, Any, List, Optional, Callable
from ..services.java_service_bridge import JavaServiceBridge
from ..llm.groq_client import GroqRecipeClient
from ..memory.memory_manager import MemoryManager
import json
import logging

logger = logging.getLogger(__name__)

class FunctionCallingAgent:
    """Industry-grade agentic system using function calling"""
    
    def __init__(self):
        self.service_bridge = JavaServiceBridge()
        self.llm_client = GroqRecipeClient()
        self.memory = MemoryManager()
        self.tools = self._register_tools()
        
    def _register_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register all available tools with their schemas"""
        return {
            "get_inventory": {
                "description": "Get all inventory items in the kitchen",
                "parameters": {"type": "object", "properties": {}, "required": []},
                "function": self._get_inventory
            },
            "search_inventory": {
                "description": "Search inventory items by name or category",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Search term"}},
                    "required": ["query"]
                },
                "function": self._search_inventory
            },
            "add_inventory": {
                "description": "Add new item or increase quantity of existing item",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Item name"},
                        "quantity": {"type": "number", "description": "Quantity to add"}
                    },
                    "required": ["name", "quantity"]
                },
                "function": self._add_inventory
            },
            "consume_inventory": {
                "description": "Consume/reduce quantity of an inventory item",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Item name"},
                        "quantity": {"type": "number", "description": "Quantity to consume"}
                    },
                    "required": ["name", "quantity"]
                },
                "function": self._consume_inventory
            },
            "get_low_stock": {
                "description": "Get items that are running low in stock",
                "parameters": {"type": "object", "properties": {}, "required": []},
                "function": self._get_low_stock
            },
            "get_shopping_lists": {
                "description": "Get shopping lists and suggested items to buy",
                "parameters": {"type": "object", "properties": {}, "required": []},
                "function": self._get_shopping_lists
            },
            "generate_recipes": {
                "description": "Generate recipes based on available inventory",
                "parameters": {
                    "type": "object",
                    "properties": {"servings": {"type": "number", "description": "Number of servings"}},
                    "required": []
                },
                "function": self._generate_recipes
            }
        }
    
    async def process_request(self, user_message: str, kitchen_id: int, user_email: str) -> Dict[str, Any]:
        """Process user request using function calling"""
        
        session_id = f"{user_email}_{kitchen_id}"
        
        # Use function calling to determine and execute actions
        result = await self._function_calling_workflow(user_message, kitchen_id, user_email)
        
        # Generate natural response
        response = await self._generate_response(user_message, result)
        
        # Store in memory
        self.memory.add_interaction(session_id, user_message, response, {"result": result})
        
        return {
            "response": response,
            "function_calls": result.get("function_calls", []),
            "result": result
        }
    
    async def _function_calling_workflow(self, user_message: str, kitchen_id: int, user_email: str) -> Dict[str, Any]:
        """Execute function calling workflow"""
        
        # Create function calling prompt
        tools_schema = self._create_tools_schema()
        
        system_prompt = f"""You are PantryMind AI assistant. Use the available functions to help users manage their kitchen inventory.

Available functions:
{json.dumps(tools_schema, indent=2)}

Based on the user's message, call the appropriate function(s). You can call multiple functions if needed.

Return your response in this format:
{{
  "function_calls": [
    {{
      "name": "function_name",
      "arguments": {{"param": "value"}}
    }}
  ],
  "reasoning": "Why you chose these functions"
}}"""

        try:
            # Get function calls from LLM
            response = await self.llm_client.text_completion(
                prompt=f"{system_prompt}\n\nUser: {user_message}\n\nResponse:",
                max_tokens=300,
                temperature=0.1
            )
            
            function_response = json.loads(response)
            function_calls = function_response.get("function_calls", [])
            
            # Execute function calls
            results = []
            for call in function_calls:
                func_name = call.get("name")
                func_args = call.get("arguments", {})
                
                if func_name in self.tools:
                    # Add context parameters
                    func_args["kitchen_id"] = kitchen_id
                    func_args["user_email"] = user_email
                    
                    # Execute function
                    func_result = await self.tools[func_name]["function"](**func_args)
                    results.append({
                        "function": func_name,
                        "arguments": func_args,
                        "result": func_result
                    })
            
            return {
                "function_calls": function_calls,
                "results": results,
                "reasoning": function_response.get("reasoning", "")
            }
            
        except Exception as e:
            logger.error(f"Function calling failed: {e}")
            # Fallback to simple inventory check
            inventory = await self._get_inventory(kitchen_id=kitchen_id)
            return {
                "function_calls": [{"name": "get_inventory", "arguments": {}}],
                "results": [{"function": "get_inventory", "result": inventory}],
                "reasoning": "Fallback to inventory display"
            }
    
    def _create_tools_schema(self) -> List[Dict[str, Any]]:
        """Create OpenAI-compatible tools schema"""
        schema = []
        for name, tool in self.tools.items():
            schema.append({
                "name": name,
                "description": tool["description"],
                "parameters": tool["parameters"]
            })
        return schema
    
    # Tool implementations
    async def _get_inventory(self, kitchen_id: int, **kwargs) -> List[Dict[str, Any]]:
        return await self.service_bridge.get_inventory_by_kitchen(kitchen_id)
    
    async def _search_inventory(self, query: str, kitchen_id: int, **kwargs) -> List[Dict[str, Any]]:
        all_items = await self.service_bridge.get_inventory_by_kitchen(kitchen_id)
        query_lower = query.lower()
        return [item for item in all_items 
                if query_lower in item.get('name', '').lower() or 
                   query_lower in item.get('categoryName', '').lower()]
    
    async def _add_inventory(self, name: str, quantity: int, kitchen_id: int, **kwargs) -> Dict[str, Any]:
        try:
            # Check if item exists
            all_items = await self.service_bridge.get_inventory_by_kitchen(kitchen_id)
            existing_item = next((item for item in all_items 
                                if item.get('name', '').lower() == name.lower()), None)
            
            if existing_item:
                # Update existing
                current_qty = existing_item.get('totalQuantity', 0)
                new_qty = current_qty + quantity
                items = existing_item.get('items', [])
                if items:
                    await self.service_bridge.update_inventory_item(items[0].get('id'), new_qty)
                    return {"success": True, "message": f"Added {quantity} to {name}. Total: {new_qty}"}
            else:
                # Create new
                await self.service_bridge.add_inventory_manual(kitchen_id, name, quantity, 6, 3, 1)
                return {"success": True, "message": f"Added new item: {name} ({quantity})"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _consume_inventory(self, name: str, quantity: int, kitchen_id: int, **kwargs) -> Dict[str, Any]:
        try:
            all_items = await self.service_bridge.get_inventory_by_kitchen(kitchen_id)
            existing_item = next((item for item in all_items 
                                if item.get('name', '').lower() == name.lower()), None)
            
            if not existing_item:
                return {"error": f"Item '{name}' not found"}
            
            current_qty = existing_item.get('totalQuantity', 0)
            if current_qty < quantity:
                return {"error": f"Not enough {name}. Available: {current_qty}"}
            
            new_qty = current_qty - quantity
            items = existing_item.get('items', [])
            if items:
                await self.service_bridge.update_inventory_item(items[0].get('id'), new_qty)
                return {"success": True, "message": f"Consumed {quantity} of {name}. Remaining: {new_qty}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_low_stock(self, kitchen_id: int, **kwargs) -> List[Dict[str, Any]]:
        return await self.service_bridge.get_low_stock_items(kitchen_id)
    
    async def _get_shopping_lists(self, kitchen_id: int, **kwargs) -> List[Dict[str, Any]]:
        return await self.service_bridge.get_shopping_lists(kitchen_id)
    
    async def _generate_recipes(self, kitchen_id: int, servings: int = 4, **kwargs) -> Dict[str, Any]:
        return await self.service_bridge.generate_recipes(kitchen_id, servings)
    
    async def _generate_response(self, user_message: str, result: Dict[str, Any]) -> str:
        """Generate natural language response from function results"""
        
        system_prompt = """Generate a helpful, natural response based on the function results.

For inventory items: Show name, quantity, unit in clean format
For operations: Confirm what was done
For errors: Explain clearly what went wrong

Keep responses conversational and helpful."""

        context = f"User: {user_message}\nFunction results: {json.dumps(result, indent=2)[:1500]}"
        
        try:
            response = await self.llm_client.text_completion(
                prompt=f"{system_prompt}\n\n{context}\n\nResponse:",
                max_tokens=300,
                temperature=0.3
            )
            return response.strip()
        except Exception as e:
            return "Operation completed successfully!"