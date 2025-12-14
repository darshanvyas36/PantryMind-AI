# app/services/recipe_service_new.py
from app.models.recipe import RecipeRequest, RecipeResponse, Recipe
from app.core.ai.pipeline import ai_pipeline
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class RecipeService:
    def __init__(self):
        self.recipe_count = 4
        self.base_cooking_time = 20
        self.time_increment = 5
        self.fallback_cooking_time = 15
    
    async def generate_recipes(self, request: RecipeRequest, category: str = None) -> RecipeResponse:
        try:
            # Create inventory summary
            inventory_summary = []
            for item in request.items:
                unit = self._standardize_unit(item.unit, item.quantity)
                inventory_summary.append(f"- {item.name}: {unit['quantity']} {unit['unit']}")
            
            inventory_text = "\n".join(inventory_summary)
            
            # Use AI pipeline
            inventory_data = {
                "inventory_text": inventory_text,
                "servings": request.servings,
                "category": category or "general"
            }
            
            schema_result = await ai_pipeline.process_recipe_generation(inventory_data, category)
            converted_recipes = self._convert_recipes(schema_result.recipes, request)
            
            logger.info(f"Generated {len(converted_recipes)} recipes using AI pipeline")
            return RecipeResponse(recipes=converted_recipes)
            
        except Exception as e:
            logger.error(f"Recipe generation failed: {e}")
            return self._create_fallback_recipes(request.servings, request.items)
    
    async def generate_recipe_by_name(self, request) -> RecipeResponse:
        try:
            inventory_summary = []
            for item in request.availableItems:
                inventory_summary.append(f"- {item['name']}: {item['quantity']} {item['unit']}")
            
            inventory_data = {
                "inventory_text": "\n".join(inventory_summary),
                "servings": request.servings,
                "recipe_name": request.recipeName
            }
            
            schema_result = await ai_pipeline.process_recipe_generation(inventory_data)
            converted_recipes = self._convert_recipes(schema_result.recipes, request)
            
            return RecipeResponse(recipes=converted_recipes)
            
        except Exception as e:
            logger.error(f"Recipe by name failed: {e}")
            recipe = Recipe(
                name=f"Default Recipe - {request.recipeName}",
                ingredients=["Basic ingredients"],
                missing_items=["Check recipe online"],
                steps=["Search for recipe online"],
                servings=request.servings,
                cooking_time="30 mins"
            )
            return RecipeResponse(recipes=[recipe])
    
    def _convert_recipes(self, recipes_data, request):
        converted_recipes = []
        
        for i, recipe_data in enumerate(recipes_data):
            ingredients = []
            for item in recipe_data.inventory_items_used:
                ingredients.append(f"{item.name}: {item.quantity} {item.unit}")
            
            missing_items = []
            for item in recipe_data.missing_items:
                missing_items.append(f"{item.name}: {item.quantity} {item.unit}")
            
            recipe = Recipe(
                name=recipe_data.recipe_name,
                ingredients=ingredients,
                missing_items=missing_items,
                steps=recipe_data.steps,
                servings=request.servings,
                cooking_time=f"{self.base_cooking_time + i*self.time_increment} mins"
            )
            converted_recipes.append(recipe)
        
        return converted_recipes
    
    def _standardize_unit(self, unit, quantity):
        unit_lower = unit.lower().strip()
        
        if unit_lower in ['kg', 'kilogram', 'kilograms']:
            return {'quantity': quantity * 1000, 'unit': 'g'}
        elif unit_lower in ['g', 'gram', 'grams', 'gm']:
            return {'quantity': quantity, 'unit': 'g'}
        elif unit_lower in ['l', 'liter', 'liters', 'litre', 'litres']:
            return {'quantity': quantity * 1000, 'unit': 'ml'}
        elif unit_lower in ['ml', 'milliliter', 'milliliters']:
            return {'quantity': quantity, 'unit': 'ml'}
        elif unit_lower in ['dozen', 'doz']:
            return {'quantity': quantity * 12, 'unit': 'pcs'}
        elif unit_lower in ['pcs', 'piece', 'pieces', 'pc', 'count', 'nos']:
            return {'quantity': quantity, 'unit': 'pcs'}
        else:
            return {'quantity': quantity, 'unit': 'pcs'}
    
    def _create_fallback_recipes(self, servings: int, available_items) -> RecipeResponse:
        ingredients = []
        for item in available_items[:3]:
            unit_data = self._standardize_unit(item.unit, item.quantity)
            ingredients.append(f"{item.name}: {unit_data['quantity']} {unit_data['unit']}")
        
        recipe = Recipe(
            name="This is sample recipe",
            ingredients=ingredients if ingredients else ["Basic ingredients"],
            missing_items=["Basic spices: 10g"],
            steps=["Use available ingredients", "Cook as desired", "Season and serve"],
            servings=servings,
            cooking_time=f"{self.fallback_cooking_time} mins"
        )
        
        return RecipeResponse(recipes=[recipe])