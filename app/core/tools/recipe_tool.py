# app/core/tools/recipe_tool.py
from typing import Dict, Any, List
from .base_tool import BaseTool

class RecipeSearchTool(BaseTool):
    """Tool for finding recipes based on available ingredients"""
    
    @property
    def name(self) -> str:
        return "recipe_search"
    
    @property
    def description(self) -> str:
        return "Find recipes based on available ingredients and dietary preferences"
    
    async def _run(self, kitchen_id: int, ingredient_list: List[str] = None, 
                   dietary_preferences: List[str] = None) -> Dict[str, Any]:
        """
        Search for recipes using available ingredients
        
        Args:
            kitchen_id: Kitchen ID to check ingredient availability
            ingredient_list: Specific ingredients to search for
            dietary_preferences: Dietary restrictions/preferences
        """
        
        # First get current inventory to check ingredient availability
        inventory_params = {"kitchenId": kitchen_id}
        inventory_data = await self._make_api_call("/api/inventory", inventory_params)
        
        # Extract available ingredients
        available_ingredients = []
        for item in inventory_data:
            if item.get("totalQuantity", 0) > 0:
                available_ingredients.append(item.get("name", "").lower())
        
        # Generate recipe suggestions based on available ingredients
        recipe_suggestions = self._generate_recipe_suggestions(
            available_ingredients, ingredient_list, dietary_preferences
        )
        
        return {
            "available_ingredients": available_ingredients,
            "ingredient_count": len(available_ingredients),
            "recipe_suggestions": recipe_suggestions,
            "dietary_preferences": dietary_preferences or []
        }
    
    def _generate_recipe_suggestions(self, available: List[str], 
                                   requested: List[str] = None,
                                   dietary: List[str] = None) -> List[Dict[str, Any]]:
        """Generate recipe suggestions based on available ingredients"""
        
        # Simple recipe matching logic (can be enhanced with ML/AI later)
        suggestions = []
        
        # Common recipe patterns
        recipe_patterns = [
            {
                "name": "Vegetable Stir Fry",
                "required": ["vegetables", "oil"],
                "optional": ["soy sauce", "garlic", "ginger"],
                "type": "vegetarian"
            },
            {
                "name": "Pasta with Vegetables", 
                "required": ["pasta", "vegetables"],
                "optional": ["cheese", "herbs", "tomatoes"],
                "type": "vegetarian"
            },
            {
                "name": "Rice Bowl",
                "required": ["rice"],
                "optional": ["vegetables", "protein", "sauce"],
                "type": "flexible"
            }
        ]
        
        for pattern in recipe_patterns:
            # Check if we have required ingredients
            has_required = any(
                any(req in ingredient for ingredient in available)
                for req in pattern["required"]
            )
            
            if has_required:
                # Calculate availability score
                available_optional = sum(
                    1 for opt in pattern["optional"]
                    if any(opt in ingredient for ingredient in available)
                )
                
                score = (available_optional / len(pattern["optional"])) * 100
                
                suggestions.append({
                    "name": pattern["name"],
                    "availability_score": round(score, 1),
                    "type": pattern["type"],
                    "missing_ingredients": [
                        opt for opt in pattern["optional"]
                        if not any(opt in ingredient for ingredient in available)
                    ]
                })
        
        # Sort by availability score
        suggestions.sort(key=lambda x: x["availability_score"], reverse=True)
        
        return suggestions[:5]  # Return top 5 suggestions