# app/core/tools/category_tool.py
from typing import Dict, Any
from .base_tool import BaseTool

class CategoryLookupTool(BaseTool):
    """Tool for fetching available categories and units"""
    
    @property
    def name(self) -> str:
        return "category_lookup"
    
    @property
    def description(self) -> str:
        return "Get available categories and measurement units"
    
    async def _run(self) -> Dict[str, Any]:
        """Fetch categories and units from Java backend"""
        
        # Fetch categories and units
        categories = await self._make_api_call("/api/categories")
        units = await self._make_api_call("/api/units")
        
        return {
            "categories": categories,
            "units": units,
            "category_count": len(categories),
            "unit_count": len(units)
        }