import json
import logging
import requests
from typing import List, Dict, Any, Set
import google.generativeai as genai
from app.config.settings import settings

logger = logging.getLogger(__name__)

class AIShoppingService:
    def __init__(self, backend_url: str = "http://localhost:8080"):
        self.backend_url = backend_url
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def generate_smart_suggestions(self, request) -> Dict[str, Any]:
        try:
            kitchen_id = request.kitchenId if hasattr(request, 'kitchenId') else request.get('kitchenId')
            list_type = request.listType if hasattr(request, 'listType') else request.get('listType', 'WEEKLY')
            existing_items = request.existingItems if hasattr(request, 'existingItems') else request.get('existingItems', [])
            
            all_existing = self._get_all_existing_items(kitchen_id, list_type, existing_items)
            inventory_data = self._get_inventory_data(kitchen_id)
            suggestions = self._generate_unique_suggestions(inventory_data, list_type, all_existing)
            
            return {
                "suggestions": suggestions,
                "totalSuggestions": len(suggestions),
                "listType": list_type
            }
        except Exception as e:
            logger.error(f"Error generating AI suggestions: {str(e)}")
            return {"suggestions": [], "totalSuggestions": 0, "listType": list_type}

    def _get_all_existing_items(self, kitchen_id: int, list_type: str, existing_items: List[str]) -> Set[str]:
        all_items = set()
        all_items.update(item.lower().strip() for item in existing_items)
        
        try:
            response = requests.get(f"{self.backend_url}/api/shopping-lists?kitchenId={kitchen_id}")
            if response.status_code == 200:
                lists = response.json()
                current_list = next((l for l in lists if l['listType'] == list_type), None)
                if current_list and 'items' in current_list:
                    all_items.update(item['canonicalName'].lower().strip() for item in current_list['items'])
        except Exception as e:
            logger.error(f"Error fetching shopping list items: {str(e)}")
        
        return all_items

    def _generate_unique_suggestions(self, inventory_data: List[Dict], list_type: str, existing_items: Set[str]) -> List[Dict]:
        suggestions = []
        low_stock_items = [item for item in inventory_data if self._is_low_stock(item)]
        
        for item in low_stock_items:
            item_name_lower = item['name'].lower().strip()
            
            if item_name_lower in existing_items:
                continue
                
            unit_obj = item.get('unit', {})
            unit_name = unit_obj.get('name', 'pieces') if unit_obj else 'pieces'
            quantity = self._calculate_smart_quantity(item, list_type, unit_name)
            
            suggestions.append({
                "name": item['name'],
                "quantity": quantity,
                "unit": unit_name,
                "reason": "Low stock - needs restocking",
                "confidence": 0.8,
                "priority": "high"
            })
            
            existing_items.add(item_name_lower)
            
            if len(suggestions) >= self._get_suggestion_count(list_type):
                break
        
        return suggestions

    def _calculate_smart_quantity(self, item: Dict, list_type: str, unit_name: str) -> float:
        multipliers = {"DAILY": 1, "WEEKLY": 2, "MONTHLY": 5, "RANDOM": 3}
        multiplier = multipliers.get(list_type, 2)
        
        unit_lower = unit_name.lower()
        item_name_lower = item.get('name', '').lower()
        
        if 'gram' in unit_lower:
            if any(word in item_name_lower for word in ['rice', 'flour', 'dal', 'wheat']):
                return multiplier * 1000
            elif any(word in item_name_lower for word in ['spice', 'salt', 'sugar', 'masala']):
                return multiplier * 250
            else:
                return multiplier * 500
        elif 'kg' in unit_lower:
            return multiplier * 1
        elif 'liter' in unit_lower or 'litre' in unit_lower:
            return multiplier * 1
        elif 'ml' in unit_lower:
            return multiplier * 500
        else:
            return multiplier * 3

    def _get_suggestion_count(self, list_type: str) -> int:
        return {"DAILY": 3, "WEEKLY": 5, "MONTHLY": 8, "RANDOM": 4}.get(list_type, 5)

    def _get_inventory_data(self, kitchen_id: int) -> List[Dict]:
        try:
            response = requests.get(f"{self.backend_url}/api/inventory?kitchenId={kitchen_id}")
            return response.json() if response.status_code == 200 else []
        except Exception as e:
            logger.error(f"Error fetching inventory: {str(e)}")
            return []

    def _is_low_stock(self, item: Dict) -> bool:
        current_qty = item.get("totalQuantity", 0)
        min_stock = item.get("minStock", 5)
        return current_qty <= min_stock

    def analyze_consumption_patterns(self, kitchen_id: int) -> Dict[str, Any]:
        try:
            inventory_data = self._get_inventory_data(kitchen_id)
            low_stock_count = len([item for item in inventory_data if self._is_low_stock(item)])
            
            return {
                "totalItems": len(inventory_data),
                "lowStockItems": low_stock_count,
                "consumptionTrends": [{"category": "Low Stock", "count": low_stock_count, "trend": "needs_attention"}],
                "recommendations": ["Restock low inventory items"]
            }
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            return {"totalItems": 0, "lowStockItems": 0, "consumptionTrends": [], "recommendations": []}
