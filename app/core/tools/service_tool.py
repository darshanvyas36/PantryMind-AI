# app/core/tools/service_tool.py
from typing import Dict, Any
from .base_tool import BaseTool
from app.core.services.java_service_bridge import JavaServiceBridge

class ServiceTool(BaseTool):
    """Tool that uses Java service methods directly with ALL input options"""
    
    def __init__(self):
        super().__init__()
        self.service_bridge = JavaServiceBridge()
    
    @property
    def name(self) -> str:
        return "service_tool"
    
    @property
    def description(self) -> str:
        return """Complete service tool for PantryMind operations with ALL input methods.
        
        Operations:
        - get_inventory: View inventory items
        - get_low_stock: Find low stock items  
        - get_expired: Find expired items
        - add_inventory_manual: Add item manually (name, quantity, categoryId, unitId, description, locationId, expiryDate, price)
        - add_inventory_bill: Add items from bill image (OCR processing)
        - add_inventory_label: Add item from product label (OCR processing)  
        - add_inventory_product: Add items from product/shelf image (AI detection, mode: single/shelf/auto)
        - update_inventory: Update existing item (item_id + fields to update)
        - delete_inventory: Delete item (item_id)
        - add_to_shopping_list: Add item to shopping list (name, quantity, unitId, categoryId)
        - get_shopping_lists: View shopping lists
        - get_categories: Get all categories
        - get_units: Get all units
        """
    
    async def _run(self, operation: str, kitchen_id: int, **kwargs) -> Dict[str, Any]:
        """Execute service operations with full support for all input methods"""
        
        if operation == "get_inventory":
            result = await self.service_bridge.get_inventory_by_kitchen(kitchen_id)
            return {"success": True, "inventory": result}
            
        elif operation == "get_low_stock":
            result = await self.service_bridge.get_low_stock_items(kitchen_id)
            return {"success": True, "low_stock_items": result}
            
        elif operation == "get_expired":
            result = await self.service_bridge.get_expired_items(kitchen_id)
            return {"success": True, "expired_items": result}
            
        # ALL 4 INVENTORY INPUT METHODS
        elif operation == "add_inventory_manual":
            name = kwargs.get("name")
            quantity = kwargs.get("quantity", 1)
            category_id = kwargs.get("category_id", 1)
            unit_id = kwargs.get("unit_id", 1)
            user_id = kwargs.get("user_id", 1)
            description = kwargs.get("description")
            location_id = kwargs.get("location_id")
            expiry_date = kwargs.get("expiry_date")
            price = kwargs.get("price")
            
            result = await self.service_bridge.add_inventory_manual(
                kitchen_id, name, quantity, category_id, unit_id, user_id,
                description, location_id, expiry_date, price
            )
            return result
            
        elif operation == "add_inventory_bill":
            user_id = kwargs.get("user_id", 1)
            result = await self.service_bridge.add_inventory_from_bill(kitchen_id, user_id)
            return result
            
        elif operation == "add_inventory_label":
            user_id = kwargs.get("user_id", 1)
            result = await self.service_bridge.add_inventory_from_label(kitchen_id, user_id)
            return result
            
        elif operation == "add_inventory_product":
            user_id = kwargs.get("user_id", 1)
            mode = kwargs.get("mode", "auto")
            result = await self.service_bridge.add_inventory_from_product(kitchen_id, user_id, mode)
            return result
            
        elif operation == "update_inventory":
            item_id = kwargs.get("item_id")
            update_data = {k: v for k, v in kwargs.items() if k != "item_id" and v is not None}
            result = await self.service_bridge.update_inventory_item(item_id, **update_data)
            return result
            
        elif operation == "delete_inventory":
            item_id = kwargs.get("item_id")
            result = await self.service_bridge.delete_inventory_item(item_id)
            return result
            
        elif operation == "add_to_shopping_list":
            name = kwargs.get("name")
            quantity = kwargs.get("quantity", 1)
            unit_id = kwargs.get("unit_id", 1)
            category_id = kwargs.get("category_id", 1)
            result = await self.service_bridge.add_to_shopping_list(kitchen_id, name, quantity, unit_id, category_id)
            return result
            
        elif operation == "get_shopping_lists":
            result = await self.service_bridge.get_shopping_lists(kitchen_id)
            return {"success": True, "shopping_lists": result}
            
        elif operation == "get_categories":
            result = await self.service_bridge.get_categories()
            return {"success": True, "categories": result}
            
        elif operation == "get_units":
            result = await self.service_bridge.get_units()
            return {"success": True, "units": result}
            
        else:
            return {"error": f"Unknown operation: {operation}"}