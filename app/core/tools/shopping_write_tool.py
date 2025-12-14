# app/core/tools/shopping_write_tool.py
from typing import Dict, Any, List
from .base_tool import BaseTool

class ShoppingWriteTool(BaseTool):
    """Tool for managing shopping lists - create, add items, mark purchased"""
    
    @property
    def name(self) -> str:
        return "shopping_write"
    
    @property
    def description(self) -> str:
        return "Manage shopping lists: create lists, add items, mark as purchased"
    
    async def _run(self, kitchen_id: int, operation: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform shopping list operations
        
        Args:
            kitchen_id: Kitchen ID
            operation: create_list, add_item, mark_purchased, delete_item
            data: Operation-specific data
        """
        
        if operation == "create_list":
            return await self._create_list(kitchen_id, data)
        elif operation == "add_item":
            return await self._add_item(kitchen_id, data)
        elif operation == "mark_purchased":
            return await self._mark_purchased(kitchen_id, data)
        elif operation == "delete_item":
            return await self._delete_item(kitchen_id, data)
        else:
            return {"error": f"Unknown operation: {operation}"}
    
    async def _create_list(self, kitchen_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new shopping list"""
        try:
            list_data = {
                "name": data.get("name", "Shopping List"),
                "type": data.get("type", "WEEKLY"),
                "kitchenId": kitchen_id
            }
            
            result = await self._make_api_call("/api/shopping-lists", method="POST", data=list_data)
            return {"success": True, "message": f"Created shopping list: {data.get('name')}", "data": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _add_item(self, kitchen_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add item to shopping list"""
        try:
            item_data = {
                "name": data.get("name"),
                "quantity": data.get("quantity", 1),
                "unitId": data.get("unitId", 1),
                "categoryId": data.get("categoryId", 1),
                "shoppingListId": data.get("listId")
            }
            
            result = await self._make_api_call("/api/shopping-lists/items", method="POST", data=item_data)
            return {"success": True, "message": f"Added {data.get('name')} to shopping list", "data": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _mark_purchased(self, kitchen_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mark shopping list item as purchased"""
        try:
            item_id = data.get("itemId")
            update_data = {
                "purchased": True,
                "purchasedDate": data.get("purchasedDate")
            }
            
            result = await self._make_api_call(f"/api/shopping-lists/items/{item_id}", method="PUT", data=update_data)
            return {"success": True, "message": f"Marked item as purchased", "data": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _delete_item(self, kitchen_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Delete item from shopping list"""
        try:
            item_id = data.get("itemId")
            await self._make_api_call(f"/api/shopping-lists/items/{item_id}", method="DELETE")
            return {"success": True, "message": f"Removed item from shopping list"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}