# app/core/tools/comprehensive_tool.py
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from ..services.java_service_bridge import JavaServiceBridge

class ComprehensivePantryTool(BaseTool):
    """Single comprehensive tool with access to ALL PantryMind endpoints"""
    
    def __init__(self):
        super().__init__()
        self.service_bridge = JavaServiceBridge()
    
    @property
    def name(self) -> str:
        return "comprehensive_pantry_tool"
    
    @property
    def description(self) -> str:
        return """Complete PantryMind operations tool. Can perform ANY task a user can do manually.
        
        Operations:
        - inventory: get, add, update, delete, consume items, check expired/low-stock
        - shopping: get lists, add items, mark purchased, generate suggestions
        - analytics: consumption patterns, waste analysis, financial summaries
        - categories: get/create categories and units
        - recipes: search recipes, get suggestions
        - notifications: get alerts and notifications
        
        Use operation parameter to specify what to do."""
    
    async def _run(self, operation: str, kitchen_id: int, **kwargs) -> Dict[str, Any]:
        """Execute comprehensive pantry operations"""
        
        if operation == "get_inventory":
            return await self._get_inventory(kitchen_id, **kwargs)
        elif operation == "get_low_stock":
            return await self._get_low_stock(kitchen_id)
        elif operation == "get_expired":
            return await self._get_expired(kitchen_id)
        elif operation == "add_inventory":
            return await self._add_inventory(kitchen_id, **kwargs)
        elif operation == "update_inventory":
            return await self._update_inventory(**kwargs)
        elif operation == "delete_inventory":
            return await self._delete_inventory(**kwargs)
        elif operation == "consume_items":
            return await self._consume_items(kitchen_id, **kwargs)
        elif operation == "get_shopping_lists":
            return await self._get_shopping_lists(kitchen_id)
        elif operation == "add_to_shopping_list":
            return await self._add_to_shopping_list(kitchen_id, **kwargs)
        elif operation == "mark_purchased":
            return await self._mark_purchased(**kwargs)
        elif operation == "get_analytics":
            return await self._get_analytics(kitchen_id, **kwargs)
        elif operation == "get_categories":
            return await self._get_categories()
        elif operation == "get_units":
            return await self._get_units()
        elif operation == "search_recipes":
            return await self._search_recipes(kitchen_id, **kwargs)
        elif operation == "get_notifications":
            return await self._get_notifications(kitchen_id)
        elif operation == "get_user_profile":
            return await self._get_user_profile(**kwargs)
        elif operation == "remove_shopping_item":
            return await self._remove_shopping_item(**kwargs)
        elif operation == "update_shopping_item":
            return await self._update_shopping_item(**kwargs)
        elif operation == "clear_shopping_list":
            return await self._clear_shopping_list(**kwargs)
        elif operation == "update_member_role":
            return await self._update_member_role(kitchen_id, **kwargs)
        elif operation == "remove_member":
            return await self._remove_member(kitchen_id, **kwargs)
        elif operation == "generate_invite_code":
            return await self._generate_invite_code(kitchen_id)
        elif operation == "create_category":
            return await self._create_category(**kwargs)
        elif operation == "create_unit":
            return await self._create_unit(**kwargs)
        elif operation == "search_inventory":
            return await self._search_inventory(kitchen_id, **kwargs)
        elif operation == "get_expiring_items":
            return await self._get_expiring_items(kitchen_id)
        else:
            return {"error": f"Unknown operation: {operation}"}
    
    async def _get_inventory(self, kitchen_id: int, **kwargs) -> Dict[str, Any]:
        """Get inventory items"""
        try:
            result = await self._make_api_call("/api/inventory", params={"kitchenId": kitchen_id})
            return {
                "success": True,
                "total_items": len(result) if isinstance(result, list) else 0,
                "inventory": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_low_stock(self, kitchen_id: int) -> Dict[str, Any]:
        """Get low stock items"""
        try:
            result = await self._make_api_call(f"/api/shopping-lists/low-stock/{kitchen_id}")
            return {
                "success": True,
                "low_stock_count": len(result) if isinstance(result, list) else 0,
                "low_stock_items": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_expired(self, kitchen_id: int) -> Dict[str, Any]:
        """Get expired items"""
        try:
            result = await self._make_api_call("/api/inventory/expired", params={"kitchenId": kitchen_id})
            return {
                "success": True,
                "expired_count": len(result) if isinstance(result, list) else 0,
                "expired_items": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _add_inventory(self, kitchen_id: int, **kwargs) -> Dict[str, Any]:
        """Add inventory item"""
        try:
            data = {
                "name": kwargs.get("name"),
                "quantity": kwargs.get("quantity", 1),
                "categoryId": kwargs.get("categoryId", 1),
                "unitId": kwargs.get("unitId", 1),
                "expiryDate": kwargs.get("expiryDate"),
                "price": kwargs.get("price", 0),
                "kitchenId": kitchen_id
            }
            result = await self._make_api_call("/api/inventory", method="POST", data=data)
            return {"success": True, "message": f"Added {kwargs.get('name')} to inventory", "item": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _update_inventory(self, **kwargs) -> Dict[str, Any]:
        """Update inventory item"""
        try:
            item_id = kwargs.get("item_id")
            data = {k: v for k, v in kwargs.items() if k != "item_id" and v is not None}
            result = await self._make_api_call(f"/api/inventory/items/{item_id}", method="PUT", data=data)
            return {"success": True, "message": f"Updated item {item_id}", "item": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _delete_inventory(self, **kwargs) -> Dict[str, Any]:
        """Delete inventory item"""
        try:
            item_id = kwargs.get("item_id")
            await self._make_api_call(f"/api/inventory/items/{item_id}", method="DELETE")
            return {"success": True, "message": f"Deleted item {item_id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _consume_items(self, kitchen_id: int, **kwargs) -> Dict[str, Any]:
        """Consume inventory items"""
        try:
            data = {
                "items": kwargs.get("items", []),
                "kitchenId": kitchen_id
            }
            result = await self._make_api_call("/api/inventory/consume", method="POST", data=data)
            return {"success": True, "message": "Items consumed successfully", "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_shopping_lists(self, kitchen_id: int) -> Dict[str, Any]:
        """Get shopping lists"""
        try:
            result = await self._make_api_call("/api/shopping-lists", params={"kitchenId": kitchen_id})
            return {
                "success": True,
                "lists_count": len(result) if isinstance(result, list) else 0,
                "shopping_lists": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _add_to_shopping_list(self, kitchen_id: int, **kwargs) -> Dict[str, Any]:
        """Add item to shopping list"""
        try:
            # First get shopping lists to find the right one
            lists_result = await self._get_shopping_lists(kitchen_id)
            if not lists_result.get("success") or not lists_result.get("shopping_lists"):
                return {"success": False, "error": "No shopping lists found"}
            
            # Use first available list or create one
            list_id = lists_result["shopping_lists"][0].get("id")
            
            data = {
                "name": kwargs.get("name"),
                "quantity": kwargs.get("quantity", 1),
                "unitId": kwargs.get("unitId", 1),
                "categoryId": kwargs.get("categoryId", 1),
                "shoppingListId": list_id
            }
            
            result = await self._make_api_call(
                f"/api/shopping-lists/{list_id}/items", 
                method="POST", 
                data=data,
                params={"userId": kwargs.get("userId", 1)}
            )
            return {"success": True, "message": f"Added {kwargs.get('name')} to shopping list", "item": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _mark_purchased(self, **kwargs) -> Dict[str, Any]:
        """Mark shopping list item as purchased"""
        try:
            item_id = kwargs.get("item_id")
            result = await self._make_api_call(
                f"/api/shopping-lists/items/{item_id}/mark-purchased", 
                method="POST"
            )
            return {"success": True, "message": f"Marked item {item_id} as purchased", "item": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_analytics(self, kitchen_id: int, **kwargs) -> Dict[str, Any]:
        """Get kitchen analytics"""
        try:
            # Try multiple analytics endpoints
            endpoints = [
                f"/api/analytics/kitchen/{kitchen_id}/summary",
                f"/api/analytics/kitchen/{kitchen_id}/consumption",
                f"/api/analytics/kitchen/{kitchen_id}/waste"
            ]
            
            results = {}
            for endpoint in endpoints:
                try:
                    result = await self._make_api_call(endpoint)
                    endpoint_name = endpoint.split("/")[-1]
                    results[endpoint_name] = result
                except:
                    continue
            
            return {"success": True, "analytics": results}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_categories(self) -> Dict[str, Any]:
        """Get all categories"""
        try:
            result = await self._make_api_call("/api/categories")
            return {"success": True, "categories": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_units(self) -> Dict[str, Any]:
        """Get all units"""
        try:
            result = await self._make_api_call("/api/units")
            return {"success": True, "units": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _search_recipes(self, kitchen_id: int, **kwargs) -> Dict[str, Any]:
        """Search recipes"""
        try:
            params = {"kitchenId": kitchen_id}
            if kwargs.get("ingredients"):
                params["ingredients"] = kwargs["ingredients"]
            
            result = await self._make_api_call("/api/recipes/search", params=params)
            return {"success": True, "recipes": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_notifications(self, kitchen_id: int) -> Dict[str, Any]:
        """Get notifications"""
        try:
            result = await self._make_api_call("/api/notifications", params={"kitchenId": kitchen_id})
            return {"success": True, "notifications": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_user_profile(self, **kwargs) -> Dict[str, Any]:
        """Get user profile"""
        try:
            email = kwargs.get("email")
            result = await self.service_bridge.get_user_profile(email)
            return {"success": True, "profile": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _remove_shopping_item(self, **kwargs) -> Dict[str, Any]:
        """Remove item from shopping list"""
        try:
            item_id = kwargs.get("item_id")
            result = await self.service_bridge.remove_shopping_item(item_id)
            return {"success": True, "message": f"Removed item {item_id}", "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _update_shopping_item(self, **kwargs) -> Dict[str, Any]:
        """Update shopping list item"""
        try:
            item_id = kwargs.get("item_id")
            quantity = kwargs.get("quantity", 1)
            result = await self.service_bridge.update_shopping_item(item_id, quantity)
            return {"success": True, "message": f"Updated item {item_id}", "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _clear_shopping_list(self, **kwargs) -> Dict[str, Any]:
        """Clear shopping list"""
        try:
            list_id = kwargs.get("list_id")
            result = await self.service_bridge.clear_shopping_list(list_id)
            return {"success": True, "message": f"Cleared list {list_id}", "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _update_member_role(self, kitchen_id: int, **kwargs) -> Dict[str, Any]:
        """Update kitchen member role"""
        try:
            member_id = kwargs.get("member_id")
            role = kwargs.get("role")
            result = await self.service_bridge.update_member_role(kitchen_id, member_id, role)
            return {"success": True, "message": f"Updated member {member_id} role to {role}", "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _remove_member(self, kitchen_id: int, **kwargs) -> Dict[str, Any]:
        """Remove member from kitchen"""
        try:
            member_id = kwargs.get("member_id")
            result = await self.service_bridge.remove_kitchen_member(kitchen_id, member_id)
            return {"success": True, "message": f"Removed member {member_id}", "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_invite_code(self, kitchen_id: int) -> Dict[str, Any]:
        """Generate kitchen invite code"""
        try:
            result = await self.service_bridge.generate_invite_code(kitchen_id)
            return {"success": True, "invite_code": result.get("inviteCode"), "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _create_category(self, **kwargs) -> Dict[str, Any]:
        """Create new category"""
        try:
            name = kwargs.get("name")
            description = kwargs.get("description", "")
            result = await self.service_bridge.create_category(name, description)
            return {"success": True, "message": f"Created category {name}", "category": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _create_unit(self, **kwargs) -> Dict[str, Any]:
        """Create new unit"""
        try:
            name = kwargs.get("name")
            abbreviation = kwargs.get("abbreviation", "")
            result = await self.service_bridge.create_unit(name, abbreviation)
            return {"success": True, "message": f"Created unit {name}", "unit": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _search_inventory(self, kitchen_id: int, **kwargs) -> Dict[str, Any]:
        """Search inventory items"""
        try:
            query = kwargs.get("query", "")
            result = await self.service_bridge.search_inventory(kitchen_id, query)
            return {"success": True, "search_results": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_expiring_items(self, kitchen_id: int) -> Dict[str, Any]:
        """Get expiring items"""
        try:
            result = await self.service_bridge.get_expiring_items(kitchen_id)
            return {"success": True, "expiring_items": result}
        except Exception as e:
            return {"success": False, "error": str(e)}