# app/core/tools/inventory_tool.py
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool

class InventoryLookupTool(BaseTool):
    """Tool for fetching current inventory items"""
    
    @property
    def name(self) -> str:
        return "inventory_lookup"
    
    @property
    def description(self) -> str:
        return "Fetch current inventory items for a kitchen with optional filters"
    
    async def _run(self, kitchen_id: int, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Fetch inventory data from Java backend
        
        Args:
            kitchen_id: Kitchen ID to fetch inventory for
            filters: Optional filters (category, low_stock, expiring_soon)
        """
        params = {"kitchenId": kitchen_id}
        
        # Get main inventory
        inventory_data = await self._make_api_call("/api/inventory", params)
        
        # Get expired items
        expired_data = await self._make_api_call("/api/inventory/expired", params)
        
        # Process and filter data
        result = {
            "inventory_items": inventory_data,
            "expired_items": expired_data,
            "total_items": len(inventory_data),
            "expired_count": len(expired_data)
        }
        
        # Apply filters if provided
        if filters:
            if filters.get("low_stock"):
                result["low_stock_items"] = [
                    item for item in inventory_data 
                    if item.get("totalQuantity", 0) <= item.get("lowStockThreshold", 0)
                ]
            
            if filters.get("expiring_soon"):
                result["expiring_soon"] = expired_data[:5]  # Top 5 expiring
        
        return result