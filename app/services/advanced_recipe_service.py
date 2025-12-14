# app/services/advanced_recipe_service_new.py
import asyncio
from typing import List, Dict, Any
from app.models.advanced_recipe import (
    AdvancedRecipeRequest, AdvancedRecipeResponse, AdvancedRecipe, 
    RecipeType, SkillLevel
)
from app.core.ai.pipeline import ai_pipeline
import logging

logger = logging.getLogger(__name__)

class AdvancedRecipeService:
    def __init__(self):
        self.temperature = 0.7
        self.max_tokens = 4000
    
    async def generate_advanced_recipes(self, request: AdvancedRecipeRequest) -> AdvancedRecipeResponse:
        try:
            # Create inventory summary
            inventory_summary = self._create_inventory_summary(request.items)
            inventory_text = "\n".join(inventory_summary)
            
            # Fix recipe type if None
            if request.recipe_type is None:
                request.recipe_type = RecipeType.REGULAR
            
            # Get preferences
            preferences = self._extract_preferences(request)
            
            # Use AI pipeline for recipe generation
            inventory_data = {
                "inventory_text": inventory_text,
                "servings": request.servings,
                "recipe_type": str(request.recipe_type),
                "preferences": preferences,
                "recipe_name": ""  # No specific recipe name for advanced recipes
            }
            
            schema_result = await ai_pipeline.process_recipe_generation(inventory_data)
            converted_recipes = self._convert_to_advanced_recipes(schema_result.recipes, request)
            
            # Ensure we have exactly 4 recipes for advanced recipe requests
            while len(converted_recipes) < 4:
                fallback_recipe = self._create_fallback_recipe(len(converted_recipes) + 1, request)
                converted_recipes.append(fallback_recipe)
            
            logger.info(f"Generated {len(converted_recipes)} advanced recipes")
            
            return AdvancedRecipeResponse(
                recipes=converted_recipes,
                recipe_type=str(request.recipe_type),
                total_recipes=len(converted_recipes),
                expiring_items_used=self._get_expiring_items_used(request),
                wastage_prevented=str(request.recipe_type) in ["EXPIRY_BASED", "WASTAGE_PREVENTION"]
            )
            
        except Exception as e:
            logger.error(f"Advanced recipe generation failed: {e}")
            return self._create_fallback_advanced_recipes(request)
    
    def _create_inventory_summary(self, items: List) -> List[str]:
        summary = []
        for item in items:
            unit_data = self._standardize_unit(item.unit, item.quantity)
            status = ""
            if getattr(item, 'is_expiring', False):
                status = " (EXPIRING SOON!)"
            elif getattr(item, 'is_low_stock', False):
                status = " (LOW STOCK)"
            summary.append(f"- {item.name}: {unit_data['quantity']} {unit_data['unit']}{status}")
        return summary
    
    def _extract_preferences(self, request: AdvancedRecipeRequest) -> Dict[str, Any]:
        defaults = {
            'skill_level': 'INTERMEDIATE',
            'max_cooking_time': request.maxCookingTime or 45,
            'spice_level': 'MEDIUM',
            'dietary_restrictions': [],
            'cuisine_preferences': ['Indian'],
            'avoid_ingredients': []
        }
        
        if not request.preferences or isinstance(request.preferences, str):
            return defaults
        
        if isinstance(request.preferences, dict):
            return {
                'skill_level': request.preferences.get('skill_level', 'INTERMEDIATE'),
                'max_cooking_time': request.preferences.get('maxCookingTime', 45),
                'spice_level': request.preferences.get('spice_level', 'MEDIUM'),
                'dietary_restrictions': request.preferences.get('dietary_restrictions', []),
                'cuisine_preferences': request.preferences.get('cuisine_preferences', ['Indian']),
                'avoid_ingredients': request.preferences.get('avoid_ingredients', [])
            }
        
        try:
            return {
                'skill_level': getattr(request.preferences, 'skill_level', 'INTERMEDIATE'),
                'max_cooking_time': getattr(request.preferences, 'maxCookingTime', 45),
                'spice_level': getattr(request.preferences, 'spice_level', 'MEDIUM'),
                'dietary_restrictions': getattr(request.preferences, 'dietary_restrictions', []),
                'cuisine_preferences': getattr(request.preferences, 'cuisine_preferences', ['Indian']),
                'avoid_ingredients': getattr(request.preferences, 'avoid_ingredients', [])
            }
        except:
            return defaults
    
    def _convert_to_advanced_recipes(self, recipes_data, request: AdvancedRecipeRequest) -> List[AdvancedRecipe]:
        converted_recipes = []
        preferences = self._extract_preferences(request)
        
        for i, recipe_data in enumerate(recipes_data):
            ingredients = []
            for item in recipe_data.inventory_items_used:
                ingredients.append(f"{item.name}: {item.quantity} {item.unit}")
            
            missing_items = []
            for item in recipe_data.missing_items:
                missing_items.append(f"{item.name}: {item.quantity} {item.unit}")
            
            base_time = self._calculate_cooking_time(request.recipe_type, preferences, i, request.maxCookingTime)
            
            recipe = AdvancedRecipe(
                name=recipe_data.recipe_name,
                ingredients=ingredients,
                missing_items=missing_items,
                steps=recipe_data.steps,
                servings=request.servings,
                cooking_time=f"{base_time} mins",
                difficulty_level=preferences['skill_level'],
                recipe_type=str(request.recipe_type),
                cuisine_type="Indian",
                spice_level=preferences['spice_level'],
                tips=self._generate_tips(request.recipe_type, preferences)
            )
            converted_recipes.append(recipe)
        
        return converted_recipes
    
    def _calculate_cooking_time(self, recipe_type: RecipeType, preferences: Dict, index: int, request_max_time: int = None) -> int:
        max_time = request_max_time or preferences.get('max_cooking_time', 45)
        
        if str(recipe_type) == "QUICK" or recipe_type == RecipeType.QUICK:
            time_per_recipe = max_time // 4
            calculated_time = max(5, min(time_per_recipe + (index * 2), max_time))
            return calculated_time
        
        if str(recipe_type) == "EXPIRY_BASED":
            base_time = min(25, max_time)
        else:
            base_time = min(30, max_time)
        
        return base_time + (index * 5)
    
    def _generate_tips(self, recipe_type: RecipeType, preferences: Dict) -> List[str]:
        tips = []
        
        if recipe_type == RecipeType.EXPIRY_BASED:
            tips.extend([
                "Use expiring ingredients first to prevent waste",
                "Store leftovers properly for future meals"
            ])
        elif recipe_type == RecipeType.QUICK:
            tips.extend([
                "Prep ingredients beforehand for faster cooking",
                "Use pressure cooker to reduce cooking time"
            ])
        elif recipe_type == RecipeType.WASTAGE_PREVENTION:
            tips.extend([
                "This recipe helps prevent food wastage",
                "Can be made in larger batches and frozen"
            ])
        
        skill_level = preferences.get('skill_level', 'INTERMEDIATE')
        if skill_level == 'BEGINNER':
            tips.append("Take your time and follow each step carefully")
        elif skill_level == 'ADVANCED':
            tips.append("Feel free to adjust spices and techniques to your preference")
        
        return tips
    
    def _get_expiring_items_used(self, request: AdvancedRecipeRequest) -> List[str]:
        return [item.name for item in request.expiring_items] if request.expiring_items else []
    
    def _standardize_unit(self, unit: str, quantity: int) -> Dict[str, Any]:
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
    
    def _create_fallback_recipe(self, recipe_num: int, request: AdvancedRecipeRequest) -> AdvancedRecipe:
        try:
            preferences = self._extract_preferences(request)
        except Exception:
            preferences = {'skill_level': 'INTERMEDIATE', 'spice_level': 'MEDIUM'}
        
        max_time = request.maxCookingTime or 30
        if str(request.recipe_type) == "QUICK":
            cooking_time = min(max_time, 15 + (recipe_num * 5))
        else:
            cooking_time = 20 + (recipe_num * 5)
        
        return AdvancedRecipe(
            name=f"Recipe {recipe_num} - {request.recipe_type}",
            ingredients=[f"{item.name}: {item.quantity} {item.unit}" for item in request.items[:2]],
            missing_items=["Basic spices: 5 g"],
            steps=[
                f"This is recipe {recipe_num}",
                "Use available ingredients",
                "Cook as needed"
            ],
            servings=request.servings,
            cooking_time=f"{cooking_time} mins",
            difficulty_level=preferences['skill_level'],
            recipe_type=str(request.recipe_type),
            cuisine_type="Indian",
            spice_level=preferences['spice_level'],
            tips=[f"Recipe {recipe_num} for {request.recipe_type}"]
        )
    
    def _create_fallback_advanced_recipes(self, request: AdvancedRecipeRequest) -> AdvancedRecipeResponse:
        # Create 4 fallback recipes for advanced requests
        fallback_recipes = []
        for i in range(4):
            fallback_recipes.append(self._create_fallback_recipe(i + 1, request))
        
        return AdvancedRecipeResponse(
            recipes=fallback_recipes,
            recipe_type=str(request.recipe_type),
            total_recipes=4,
            expiring_items_used=self._get_expiring_items_used(request),
            wastage_prevented=False
        )