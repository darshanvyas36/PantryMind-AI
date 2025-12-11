# app/services/enrichment_service.py
import asyncio
import httpx
from typing import Dict, List, Optional
import time
import re
import logging

logger = logging.getLogger(__name__)

class EnrichmentService:
    """Enrich extracted items with database categories and units"""
    
    def __init__(self):
        self.backend_url = "http://localhost:8080/api"
        self.cache_ttl = 1800  # 30 minutes
        self.last_fetch_time = {"categories": 0, "units": 0}
        self._categories_cache = []
        self._units_cache = []
    
    async def validate_items(self, items: List[dict], categories: List[dict], units: List[dict]) -> List[dict]:
        """Validate and fix items that LLM might have gotten wrong"""
        
        validated_items = []
        valid_categories = [cat.get("name", "").lower() for cat in categories]
        valid_units = [unit.get("name", "").lower() for unit in units]
        
        for item in items:
            validated_item = item.copy()
            
            # Validate category
            if item.get('category', '').lower() not in valid_categories:
                closest_cat = self._find_closest_category(item.get('category', ''), categories)
                if closest_cat:
                    validated_item['category'] = closest_cat
                    logger.info(f"Fixed category: {item.get('category')} → {closest_cat}")
            
            # Validate unit
            if item.get('unit', '').lower() not in valid_units:
                closest_unit = self._find_closest_unit(item.get('unit', ''), units)
                if closest_unit:
                    validated_item['unit'] = closest_unit
                    logger.info(f"Fixed unit: {item.get('unit')} → {closest_unit}")
            
            # Extract quantity from name if still missing
            if not validated_item.get('quantity') or validated_item.get('quantity') is None:
                quantity, unit = self._extract_quantity_from_name(item.get('raw_name', ''))
                if quantity:
                    validated_item['quantity'] = quantity
                    if unit and unit.lower() in valid_units:
                        validated_item['unit'] = unit
            
            validated_items.append(validated_item)
        
        return validated_items
    
    async def _get_categories(self) -> List[dict]:
        """Fetch categories from backend API with caching"""
        current_time = time.time()
        
        if (current_time - self.last_fetch_time["categories"]) < self.cache_ttl and self._categories_cache:
            return self._categories_cache
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.backend_url}/categories", timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    self._categories_cache = data
                    self.last_fetch_time["categories"] = current_time
                    logger.info(f"Fetched {len(self._categories_cache)} categories from backend")
                    return self._categories_cache
                else:
                    logger.error(f"Failed to fetch categories: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching categories from backend: {str(e)}")
        
        return []
    
    async def _get_units(self) -> List[dict]:
        """Fetch units from backend API with caching"""
        current_time = time.time()
        
        if (current_time - self.last_fetch_time["units"]) < self.cache_ttl and self._units_cache:
            return self._units_cache
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.backend_url}/units", timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    self._units_cache = data
                    self.last_fetch_time["units"] = current_time
                    logger.info(f"Fetched {len(self._units_cache)} units from backend")
                    return self._units_cache
                else:
                    logger.error(f"Failed to fetch units: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching units from backend: {str(e)}")
        
        return []
    
    def _find_closest_category(self, category: str, categories: List[dict]) -> Optional[str]:
        """Find closest matching category"""
        if not category:
            return None
        
        category_lower = category.lower()
        
        # Try exact match first
        for cat in categories:
            if cat.get("name", "").lower() == category_lower:
                return cat["name"]
        
        # Try partial matches
        for cat in categories:
            cat_name = cat.get("name", "").lower()
            if category_lower in cat_name or cat_name in category_lower:
                return cat["name"]
        
        # Try common mappings
        category_mappings = {
            "packaged food": ["staples", "grocery"],
            "personal care": ["household", "care"],
            "bakery": ["staples", "bread"],
            "frozen": ["dairy", "frozen"],
            "household": ["cleaning", "home"],
            "beverages": ["drinks", "juice"],
            "fruits": ["fruit", "fresh"],
            "vegetables": ["veggie", "produce"],
            "spices": ["seasoning", "herbs"]
        }
        
        for mapping_key, alternatives in category_mappings.items():
            if category_lower in alternatives or any(alt in category_lower for alt in alternatives):
                for cat in categories:
                    if mapping_key in cat.get("name", "").lower():
                        return cat["name"]
        
        return None
    
    def _find_closest_unit(self, unit: str, units: List[dict]) -> Optional[str]:
        """Find closest matching unit"""
        if not unit:
            # Return piece as default
            piece_unit = next((u["name"] for u in units if "piece" in u.get("name", "").lower()), None)
            return piece_unit or (units[0]["name"] if units else "piece")
        
        unit_lower = unit.lower()
        
        # Try exact match first
        for u in units:
            if u.get("name", "").lower() == unit_lower:
                return u["name"]
        
        # Try common unit aliases
        unit_aliases = {
            "ml": ["milliliter", "millilitre"],
            "l": ["litre", "liter", "ltr"],
            "g": ["grams", "gram", "gm"],
            "kg": ["kilogram", "kilo"],
            "piece": ["pcs", "pc", "nos", "pieces"],
            "dozen": ["dz"]
        }
        
        for unit_name, aliases in unit_aliases.items():
            if unit_lower in aliases or unit_lower == unit_name:
                for u in units:
                    if unit_name in u.get("name", "").lower():
                        return u["name"]
        
        # Try partial matches
        for u in units:
            unit_name = u.get("name", "").lower()
            if unit_lower in unit_name or unit_name in unit_lower:
                return u["name"]
        
        # Default fallback to piece
        piece_unit = next((u["name"] for u in units if "piece" in u.get("name", "").lower()), None)
        return piece_unit or unit
    
    def _extract_quantity_from_name(self, raw_name: str) -> tuple[Optional[float], Optional[str]]:
        """Extract quantity and unit from raw product name"""
        if not raw_name:
            return None, None
        
        # Patterns to match quantity and unit
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(ml|l|ltr|litre|liter|g|gm|grams|gram|kg|kilo|kilogram|pcs|pc|piece)',
            r'(\d+(?:\.\d+)?)\s*(ML|L|LTR|LITRE|LITER|G|GM|GRAMS|GRAM|KG|KILO|KILOGRAM|PCS|PC|PIECE)',
            r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*(ml|g|gm|ML|G|GM)',  # e.g., "2x500ml"
            r'(\d+(?:\.\d+)?)\s*X\s*(\d+(?:\.\d+)?)\s*(ML|G|GM)',  # uppercase X
        ]
        
        for pattern in patterns:
            match = re.search(pattern, raw_name)
            if match:
                if len(match.groups()) == 3:  # Pattern with multiplication
                    qty1, qty2, unit = match.groups()
                    return float(qty1) * float(qty2), unit.lower()
                else:
                    quantity, unit = match.groups()
                    return float(quantity), unit.lower()
        
        return None, None
    
    async def refresh_cache(self):
        """Force refresh of categories and units cache"""
        self.last_fetch_time = {"categories": 0, "units": 0}
        self._categories_cache = []
        self._units_cache = []
        await self._get_categories()
        await self._get_units()
        logger.info("Enrichment cache refreshed")
    
    def get_cached_categories(self) -> List[dict]:
        """Get cached categories without API call"""
        return self._categories_cache
    
    def get_cached_units(self) -> List[dict]:
        """Get cached units without API call"""
        return self._units_cache
    
    async def enrich_items_legacy(self, items: List[dict]) -> List[dict]:
        """Legacy method for backward compatibility"""
        categories = await self._get_categories()
        units = await self._get_units()
        return await self.validate_items(items, categories, units)

    # Add to enrichment_service.py
    async def _get_locations(self) -> List[dict]:
        """Fetch locations from backend API with caching"""
        current_time = time.time()
        
        if not hasattr(self, '_locations_cache'):
            self._locations_cache = []
            self.last_fetch_time["locations"] = 0
        
        if (current_time - self.last_fetch_time.get("locations", 0)) < self.cache_ttl and self._locations_cache:
            return self._locations_cache
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.backend_url}/locations", timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    self._locations_cache = data
                    self.last_fetch_time["locations"] = current_time
                    logger.info(f"Fetched {len(self._locations_cache)} locations from backend")
                    return self._locations_cache
                else:
                    logger.error(f"Failed to fetch locations: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching locations from backend: {str(e)}")
        
        return []


# Global service instance
enrichment_service = EnrichmentService()
