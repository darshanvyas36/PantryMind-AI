# app/core/tools/inventory_write_tool.py
from typing import Dict, Any, Optional
from .base_tool import BaseTool

class InventoryWriteTool(BaseTool):
    """Tool for adding, updating, and deleting inventory items"""
    
    @property
    def name(self) -> str:
        return "inventory_write"
    
    @property
    def description(self) -> str:
        return "Add, update, or delete inventory items. Operations: add, update, delete, consume"
    
    async def _run(self, kitchen_id: int, operation: str, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform write operations on inventory
        
        Args:
            kitchen_id: Kitchen ID
            operation: add, update, delete, consume
            item_data: Item details (name, quantity, category, etc.)
        """
        
        if operation == "add":
            return await self._add_item(kitchen_id, item_data)
        elif operation == "update":
            return await self._update_item(kitchen_id, item_data)
        elif operation == "delete":
            return await self._delete_item(kitchen_id, item_data)
        elif operation == "consume":
            return await self._consume_item(kitchen_id, item_data)
        else:
            return {"error": f"Unknown operation: {operation}"}
    
    async def _add_item(self, kitchen_id: int, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add new inventory item"""
        try:
            # Prepare request data
            request_data = {
                "name": item_data.get("name"),
                "quantity": item_data.get("quantity", 1),
                "categoryId": item_data.get("categoryId", 1),
                "unitId": item_data.get("unitId", 1),
                "expiryDate": item_data.get("expiryDate"),
                "price": item_data.get("price", 0),
                "kitchenId": kitchen_id
            }
            
            result = await self._make_api_call("/api/inventory", method="POST", data=request_data)
            return {"success": True, "message": f"Added {item_data.get('name')} to inventory", "data": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _update_item(self, kitchen_id: int, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing inventory item"""
        try:
            item_id = item_data.get("id")
            if not item_id:
                return {"success": False, "error": "Item ID required for update"}
            
            result = await self._make_api_call(f"/api/inventory/items/{item_id}", method="PUT", data=item_data)
            return {"success": True, "message": f"Updated item {item_id}", "data": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _delete_item(self, kitchen_id: int, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Delete inventory item"""
        try:
            item_id = item_data.get("id")
            if not item_id:
                return {"success": False, "error": "Item ID required for deletion"}
            
            await self._make_api_call(f"/api/inventory/items/{item_id}", method="DELETE")
            return {"success": True, "message": f"Deleted item {item_id}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _consume_item(self, kitchen_id: int, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mark items as consumed"""
        try:
            consume_data = {
                "items": [item_data],
                "kitchenId": kitchen_id
            }
            
            result = await self._make_api_call("/api/inventory/consume", method="POST", data=consume_data)
            return {"success": True, "message": f"Consumed {item_data.get('quantity', 1)} of {item_data.get('name', 'item')}", "data": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}