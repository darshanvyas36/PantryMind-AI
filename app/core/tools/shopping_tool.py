# app/core/tools/shopping_tool.py
from typing import Dict, Any
from .base_tool import BaseTool

class ShoppingListViewTool(BaseTool):
    """Tool for viewing existing shopping lists"""
    
    @property
    def name(self) -> str:
        return "shopping_list_view"
    
    @property
    def description(self) -> str:
        return "View existing shopping lists and their status"
    
    async def _run(self, kitchen_id: int, list_type: str = "WEEKLY") -> Dict[str, Any]:
        """
        Fetch shopping list data from Java backend
        
        Args:
            kitchen_id: Kitchen ID to fetch shopping lists for
            list_type: Type of shopping list (WEEKLY, MONTHLY, etc.)
        """
        
        # Fetch shopping lists for the kitchen
        params = {"kitchenId": kitchen_id}
        
        try:
            shopping_lists = await self._make_api_call("/api/shopping-lists", params)
            
            # Process shopping list data
            active_lists = [lst for lst in shopping_lists if lst.get("status") == "ACTIVE"]
            completed_lists = [lst for lst in shopping_lists if lst.get("status") == "COMPLETED"]
            
            # Calculate statistics
            total_items = sum(len(lst.get("items", [])) for lst in active_lists)
            pending_items = sum(
                len([item for item in lst.get("items", []) if not item.get("purchased", False)])
                for lst in active_lists
            )
            
            return {
                "kitchen_id": kitchen_id,
                "active_lists": active_lists,
                "completed_lists": completed_lists,
                "statistics": {
                    "total_active_lists": len(active_lists),
                    "total_items": total_items,
                    "pending_items": pending_items,
                    "completion_rate": round((total_items - pending_items) / total_items * 100, 1) if total_items > 0 else 0
                }
            }
            
        except Exception as e:
            return {
                "kitchen_id": kitchen_id,
                "error": f"Failed to fetch shopping lists: {str(e)}",
                "active_lists": [],
                "completed_lists": [],
                "statistics": {
                    "total_active_lists": 0,
                    "total_items": 0,
                    "pending_items": 0,
                    "completion_rate": 0
                }
            }