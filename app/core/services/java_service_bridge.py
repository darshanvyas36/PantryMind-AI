# app/core/services/java_service_bridge.py
import httpx
from typing import Dict, Any, List, Optional
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class JavaServiceBridge:
    """Complete bridge to ALL Java service methods - COMPREHENSIVE"""
    
    def __init__(self):
        self.java_base = settings.java_backend_url
        self.timeout = 10.0
    
    async def _call_service_method(self, service_path: str, method_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call Java service method directly"""
        url = f"{self.java_base}/api/internal/{service_path}"
        logger.info(f"Calling Java service: {url} with data: {method_data}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=method_data,
                    headers={
                        "X-Internal-API-Key": "internal-secret-key",
                        "X-Internal-Call": "true"
                    }
                )
                logger.info(f"Java service response status: {response.status_code}")
                response.raise_for_status()
                result = response.json()
                logger.info(f"Java service response: {result}")
                return result
        except Exception as e:
            logger.error(f"Service call failed for {url}: {str(e)}")
            return {"error": str(e)}
    
    # INVENTORY OPERATIONS - ALL 4 INPUT METHODS
    async def add_inventory_manual(self, kitchen_id: int, name: str, quantity: int = 1, 
                                 category_id: int = 1, unit_id: int = 1, user_id: int = 1,
                                 description: Optional[str] = None, location_id: Optional[int] = None,
                                 expiry_date: Optional[str] = None, price: Optional[float] = None) -> Dict[str, Any]:
        """Add inventory item manually"""
        data = {
            "kitchenId": kitchen_id, "name": name, "quantity": quantity,
            "categoryId": category_id, "unitId": unit_id, "userId": user_id
        }
        if description: data["description"] = description
        if location_id: data["locationId"] = location_id
        if expiry_date: data["expiryDate"] = expiry_date
        if price: data["price"] = price
        return await self._call_service_method("inventory/add/manual", data)
    
    async def add_inventory_from_bill(self, kitchen_id: int, user_id: int = 1) -> Dict[str, Any]:
        """Add inventory items from bill image"""
        return await self._call_service_method("inventory/add/bill", {"kitchenId": kitchen_id, "userId": user_id})
    
    async def add_inventory_from_label(self, kitchen_id: int, user_id: int = 1) -> Dict[str, Any]:
        """Add inventory item from product label"""
        return await self._call_service_method("inventory/add/label", {"kitchenId": kitchen_id, "userId": user_id})
    
    async def add_inventory_from_product(self, kitchen_id: int, user_id: int = 1, mode: str = "auto") -> Dict[str, Any]:
        """Add inventory items from product/shelf image"""
        return await self._call_service_method("inventory/add/product", {"kitchenId": kitchen_id, "userId": user_id, "mode": mode})
    
    async def get_inventory_by_kitchen(self, kitchen_id: int) -> List[Dict[str, Any]]:
        """Get inventory items by kitchen ID"""
        return await self._call_service_method("inventory/getByKitchen", {"kitchenId": kitchen_id})
    
    async def get_low_stock_items(self, kitchen_id: int) -> List[Dict[str, Any]]:
        """Get low stock items with proper filtering"""
        all_items = await self.get_inventory_by_kitchen(kitchen_id)
        low_stock = []
        
        for item in all_items:
            total_qty = item.get('totalQuantity', 0)
            min_stock = item.get('minStock', 0)
            unit = item.get('unitName', '')
            
            # Consider low stock if has minStock set and current <= minStock
            # OR if quantity is very low based on unit type
            is_low = False
            if min_stock > 0 and total_qty <= min_stock:
                is_low = True
            elif min_stock == 0:
                # Default low stock thresholds
                if 'piece' in unit.lower() and total_qty <= 3:
                    is_low = True
                elif any(u in unit.lower() for u in ['gram', 'ml']) and total_qty <= 200:
                    is_low = True
            
            if is_low:
                low_stock.append(item)
        
        return low_stock
    
    async def get_expired_items(self, kitchen_id: int) -> List[Dict[str, Any]]:
        """Get expired items"""
        return await self._call_service_method("inventory/getExpired", {"kitchenId": kitchen_id})
    
    # RECIPE OPERATIONS - ALL TYPES
    async def suggest_recipes(self, kitchen_id: int, servings: int = 4, category: Optional[str] = None) -> Dict[str, Any]:
        """Get recipe suggestions"""
        data = {"kitchenId": kitchen_id, "servings": servings}
        if category: data["category"] = category
        return await self._call_service_method("recipes/suggest", data)
    
    async def get_advanced_recipes(self, kitchen_id: int, recipe_request: Dict[str, Any]) -> Dict[str, Any]:
        """Get advanced recipes with specific requirements"""
        data = {"kitchenId": kitchen_id, **recipe_request}
        return await self._call_service_method("recipes/advanced", data)
    
    async def get_expiring_recipes(self, kitchen_id: int, servings: int = 4, user_id: int = 1) -> Dict[str, Any]:
        """Get recipes for expiring ingredients"""
        data = {"kitchenId": kitchen_id, "servings": servings, "userId": user_id}
        return await self._call_service_method("recipes/expiring", data)
    
    async def get_quick_recipes(self, kitchen_id: int, max_time: int = 30, servings: int = 4, user_id: int = 1) -> Dict[str, Any]:
        """Get quick recipes under time limit"""
        data = {"kitchenId": kitchen_id, "maxTime": max_time, "servings": servings, "userId": user_id}
        return await self._call_service_method("recipes/quick", data)
    
    async def get_recipe_by_name(self, kitchen_id: int, recipe_name: str, servings: int = 4) -> Dict[str, Any]:
        """Get specific recipe by name"""
        data = {"kitchenId": kitchen_id, "recipeName": recipe_name, "servings": servings}
        return await self._call_service_method("recipes/byName", data)
    
    # SHOPPING LIST OPERATIONS
    async def get_shopping_lists(self, kitchen_id: int) -> List[Dict[str, Any]]:
        """Get shopping lists by kitchen"""
        return await self._call_service_method("shopping/getLists", {"kitchenId": kitchen_id})
    
    async def add_to_shopping_list(self, kitchen_id: int, name: str, quantity: int = 1,
                                 unit_id: int = 1, category_id: int = 1) -> Dict[str, Any]:
        """Add item to shopping list"""
        data = {"kitchenId": kitchen_id, "name": name, "quantity": quantity, "unitId": unit_id, "categoryId": category_id}
        return await self._call_service_method("shopping/addItem", data)
    
    # DASHBOARD & REPORTS
    async def get_dashboard_stats(self, email: str) -> Dict[str, Any]:
        """Get dashboard statistics"""
        return await self._call_service_method("dashboard/stats", {"email": email})
    
    async def get_financial_summary(self, email: str) -> Dict[str, Any]:
        """Get financial summary report"""
        return await self._call_service_method("dashboard/financialSummary", {"email": email})
    
    async def get_category_breakdown(self, email: str) -> Dict[str, Any]:
        """Get category breakdown report"""
        return await self._call_service_method("dashboard/categoryBreakdown", {"email": email})
    
    async def get_waste_streak(self, email: str) -> Dict[str, Any]:
        """Get waste streak report"""
        return await self._call_service_method("dashboard/wasteStreak", {"email": email})
    
    # KITCHEN MANAGEMENT
    async def get_kitchen_members(self, kitchen_id: int) -> List[Dict[str, Any]]:
        """Get kitchen members"""
        return await self._call_service_method("kitchen/getMembers", {"kitchenId": kitchen_id})
    
    async def get_kitchen_details(self, kitchen_id: int) -> Dict[str, Any]:
        """Get kitchen details"""
        return await self._call_service_method("kitchen/getDetails", {"kitchenId": kitchen_id})
    
    # CATEGORIES AND UNITS
    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all categories"""
        return await self._call_service_method("categories/getAll", {})
    
    async def get_units(self) -> List[Dict[str, Any]]:
        """Get all units"""
        return await self._call_service_method("units/getAll", {})
    
    # INVENTORY INTERNAL ENDPOINTS
    async def get_all_inventory(self, kitchen_id: int) -> List[Dict[str, Any]]:
        """Get all inventory items (internal)"""
        return await self._call_service_method("inventory/getAll", {"kitchenId": kitchen_id})
    
    async def add_inventory_item(self, kitchen_id: int, name: str, quantity: int, 
                               category_id: int, unit_id: int, user_id: int) -> Dict[str, Any]:
        """Add inventory item (internal)"""
        data = {
            "kitchenId": kitchen_id, "name": name, "quantity": quantity,
            "categoryId": category_id, "unitId": unit_id, "userId": user_id
        }
        return await self._call_service_method("inventory/add", data)
    
    async def update_inventory_item(self, item_id: int, quantity: int) -> Dict[str, Any]:
        """Update inventory item (internal)"""
        return await self._call_service_method("inventory/update", {"itemId": item_id, "quantity": quantity})
    
    async def delete_inventory_item(self, item_id: int) -> Dict[str, Any]:
        """Delete inventory item (internal)"""
        return await self._call_service_method("inventory/delete", {"itemId": item_id})
    
    async def get_expiring_items(self, kitchen_id: int) -> List[Dict[str, Any]]:
        """Get expiring items (internal)"""
        return await self._call_service_method("inventory/getExpiring", {"kitchenId": kitchen_id})
    
    async def search_inventory(self, kitchen_id: int, query: str = "") -> List[Dict[str, Any]]:
        """Search inventory items (internal)"""
        # For now, get all inventory and filter in Python since Java search isn't implemented
        all_items = await self.get_inventory_by_kitchen(kitchen_id)
        if not query:
            return all_items
        
        # Filter items based on query
        query_lower = query.lower()
        filtered_items = []
        for item in all_items:
            if (query_lower in item.get('name', '').lower() or 
                query_lower in item.get('categoryName', '').lower()):
                filtered_items.append(item)
        return filtered_items
    
    # RECIPE GENERATION
    async def generate_recipes(self, kitchen_id: int, servings: int = 4, category: Optional[str] = None) -> Dict[str, Any]:
        """Generate recipes from inventory"""
        data = {"kitchenId": kitchen_id, "servings": servings}
        if category: data["category"] = category
        return await self._call_service_method("recipes/generate", data)
    
    # USER PROFILE
    async def get_user_profile(self, email: str) -> Dict[str, Any]:
        """Get user profile"""
        return await self._call_service_method("user/getProfile", {"email": email})
    
    # SHOPPING LIST EXTENDED
    async def remove_shopping_item(self, item_id: int) -> Dict[str, Any]:
        """Remove item from shopping list"""
        return await self._call_service_method("shopping/removeItem", {"itemId": item_id})
    
    async def update_shopping_item(self, item_id: int, quantity: int) -> Dict[str, Any]:
        """Update shopping list item"""
        return await self._call_service_method("shopping/updateItem", {"itemId": item_id, "quantity": quantity})
    
    async def clear_shopping_list(self, list_id: int) -> Dict[str, Any]:
        """Clear shopping list"""
        return await self._call_service_method("shopping/clearList", {"listId": list_id})
    
    # KITCHEN EXTENDED
    async def update_member_role(self, kitchen_id: int, member_id: int, role: str) -> Dict[str, Any]:
        """Update kitchen member role"""
        return await self._call_service_method("kitchen/updateMemberRole", 
                                             {"kitchenId": kitchen_id, "memberId": member_id, "role": role})
    
    async def remove_kitchen_member(self, kitchen_id: int, member_id: int) -> Dict[str, Any]:
        """Remove member from kitchen"""
        return await self._call_service_method("kitchen/removeMember", 
                                             {"kitchenId": kitchen_id, "memberId": member_id})
    
    async def generate_invite_code(self, kitchen_id: int) -> Dict[str, Any]:
        """Generate kitchen invite code"""
        return await self._call_service_method("kitchen/generateInviteCode", {"kitchenId": kitchen_id})
    
    # CATEGORIES & UNITS EXTENDED
    async def create_category(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create new category"""
        return await self._call_service_method("categories/create", {"name": name, "description": description})
    
    async def create_unit(self, name: str, abbreviation: str = "") -> Dict[str, Any]:
        """Create new unit"""
        return await self._call_service_method("units/create", {"name": name, "abbreviation": abbreviation})