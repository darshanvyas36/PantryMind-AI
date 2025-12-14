import json
import asyncio
from typing import List, Dict, Any
from app.models.advanced_recipe import (
    AdvancedRecipeRequest, AdvancedRecipeResponse, AdvancedRecipe, 
    RecipeType, SkillLevel
)
from app.core.llm.prompts.advanced_prompts import AdvancedRecipePrompts
from app.core.llm.groq_client import groq_recipe_client

class AdvancedRecipeService:
    def __init__(self):
        self.client = groq_recipe_client
        self.temperature = 0.7
        self.max_tokens = 4000
    
    async def generate_advanced_recipes(self, request: AdvancedRecipeRequest) -> AdvancedRecipeResponse:
        print(f"🚀 [PYTHON] Advanced recipe generation started")
        print(f"📋 [PYTHON] Recipe type: {request.recipe_type}")
        print(f"📋 [PYTHON] Recipe type TYPE: {type(request.recipe_type)}")
        print(f"📋 [PYTHON] Recipe type STR: '{str(request.recipe_type)}'")
        print(f"👤 [PYTHON] User ID: {request.user_id}")
        print(f"⏱️ [PYTHON] Max cooking time: {request.maxCookingTime}")
        print(f"🍽️ [PYTHON] Servings: {request.servings}")
        print(f"🔍 [PYTHON] Request preferences type: {type(request.preferences)}")
        print(f"🔍 [PYTHON] Request preferences value: {request.preferences}")
        
        # Create inventory summary
        inventory_summary = self._create_inventory_summary(request.items)
        inventory_text = "\n".join(inventory_summary)
        
        # Fix recipe type if None
        if request.recipe_type is None:
            request.recipe_type = RecipeType.REGULAR
            print(f"⚠️ [PYTHON] Recipe type was None, defaulting to REGULAR")
        
        print(f"🔍 [PYTHON] FINAL recipe_type being used: {request.recipe_type}")
        print(f"🔍 [PYTHON] FINAL recipe_type TYPE: {type(request.recipe_type)}")
        
        # Get preferences
        try:
            preferences = self._extract_preferences(request)
            print(f"✅ [PYTHON] Preferences extracted: {preferences}")
        except Exception as e:
            print(f"❌ [PYTHON] Error extracting preferences: {e}")
            preferences = {
                'skill_level': 'INTERMEDIATE',
                'max_cooking_time': request.maxCookingTime or 45,
                'spice_level': 'MEDIUM',
                'dietary_restrictions': [],
                'cuisine_preferences': ['Indian'],
                'avoid_ingredients': []
            }
        
        # Generate appropriate prompt based on recipe type
        try:
            prompt = self._get_prompt_by_type(request, inventory_text, preferences)
            print(f"✅ [PYTHON] Prompt generated successfully for {request.recipe_type}")
            if request.recipe_type == 'QUICK':
                print(f"⚡ [PYTHON] QUICK RECIPE DETECTED - Max time should be: {request.maxCookingTime}")
        except Exception as e:
            print(f"❌ [PYTHON] Error generating prompt: {e}")
            raise e
        
        try:
            # Use Groq client with 15-second timeout
            print(f"🚀 [PYTHON] Starting Groq API call with 15s timeout...")
            content = await self.client.text_completion(
                prompt=prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout_seconds=15
            )
            print(f"✅ [PYTHON] Groq recipe response received successfully")
            print(f"📝 [PYTHON] Response length: {len(content)} characters")
            print(f"🤖 [PYTHON] RAW GROQ RESPONSE:")
            print("=" * 80)
            print(repr(content))  # Show exact content with escape characters
            print("=" * 80)
            print("FORMATTED CONTENT:")
            print(content)
            print("=" * 80)
            
            # Parse and convert response
            try:
                recipes_data = self._parse_ai_response(content)
                print(f"✅ [PYTHON] AI response parsed")
                print(f"📊 [PYTHON] PARSED RECIPES DATA:")
                print("=" * 60)
                for i, recipe in enumerate(recipes_data.get('recipes', [])):
                    print(f"Recipe {i+1}: {recipe.get('recipe_name', 'Unknown')}")
                    print(f"  Steps: {len(recipe.get('steps', []))} steps")
                    print(f"  Ingredients: {len(recipe.get('inventory_items_used', []))} items")
                print("=" * 60)
            except Exception as parse_error:
                print(f"❌ [PYTHON] Error parsing AI response: {parse_error}")
                raise parse_error
            
            try:
                converted_recipes = self._convert_to_advanced_recipes(recipes_data, request)
                print(f"✅ [PYTHON] Recipes converted")
                print(f"🍳 [PYTHON] FINAL CONVERTED RECIPES:")
                print("=" * 60)
                for i, recipe in enumerate(converted_recipes):
                    print(f"Recipe {i+1}: {recipe.name}")
                    print(f"  Cooking Time: {recipe.cooking_time}")
                    print(f"  Servings: {recipe.servings}")
                    print(f"  Type: {recipe.recipe_type}")
                print("=" * 60)
            except Exception as convert_error:
                print(f"❌ [PYTHON] Error converting recipes: {convert_error}")
                raise convert_error
            
            from app.models.advanced_recipe import AdvancedRecipeResponse
            return AdvancedRecipeResponse(
                recipes=converted_recipes,
                recipe_type=str(request.recipe_type),
                total_recipes=len(converted_recipes),
                expiring_items_used=self._get_expiring_items_used(request),
                wastage_prevented=str(request.recipe_type) in ["EXPIRY_BASED", "WASTAGE_PREVENTION"]
            )
            
        except Exception as e:
            print(f"❌ [PYTHON] Error in advanced recipe generation: {e}")
            import traceback
            print(f"❌ [PYTHON] Traceback: {traceback.format_exc()}")
            
            # Determine if it's a timeout or parsing error
            error_type = str(e)
            if "timeout" in error_type.lower() or "GROQ_TIMEOUT" in error_type:
                reason = "AI service took too long to respond - please try regenerating"
            elif "Invalid JSON" in error_type:
                reason = "AI response format error - please try regenerating"
            else:
                reason = "AI service error - please try regenerating"
            
            # Create fallback with specific error info
            fallback_response = self._create_fallback_advanced_recipes(request)
            # Manually set fallback fields since Pydantic model doesn't allow direct assignment
            fallback_dict = fallback_response.dict()
            fallback_dict['is_fallback'] = True
            fallback_dict['fallback_reason'] = reason
            
            from app.models.advanced_recipe import AdvancedRecipeResponse
            return AdvancedRecipeResponse(**fallback_dict)
    
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
        # Default preferences
        defaults = {
            'skill_level': 'INTERMEDIATE',
            'max_cooking_time': request.maxCookingTime or 45,
            'spice_level': 'MEDIUM',
            'dietary_restrictions': [],
            'cuisine_preferences': ['Indian'],
            'avoid_ingredients': []
        }
        
        # If no preferences or preferences is a string, return defaults
        if not request.preferences or isinstance(request.preferences, str):
            return defaults
        
        # If preferences is a dict, extract values safely
        if isinstance(request.preferences, dict):
            return {
                'skill_level': request.preferences.get('skill_level', 'INTERMEDIATE'),
                'max_cooking_time': request.preferences.get('maxCookingTime', 45),
                'spice_level': request.preferences.get('spice_level', 'MEDIUM'),
                'dietary_restrictions': request.preferences.get('dietary_restrictions', []),
                'cuisine_preferences': request.preferences.get('cuisine_preferences', ['Indian']),
                'avoid_ingredients': request.preferences.get('avoid_ingredients', [])
            }
        
        # If preferences is an object, try to access attributes
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
    
    def _get_prompt_by_type(self, request: AdvancedRecipeRequest, inventory_text: str, preferences: Dict[str, Any]) -> str:
        recipe_type_str = str(request.recipe_type)
        print(f"🔍 [PYTHON] Comparing recipe_type_str: '{recipe_type_str}'")
        if recipe_type_str == "EXPIRY_BASED":
            expiring_items = [item.name for item in request.expiring_items] if request.expiring_items else []
            print(f"⚠️ [PYTHON] 🔴 EXPIRY MODE: Prioritizing {len(expiring_items)} expiring items: {expiring_items}")
            return AdvancedRecipePrompts.expiry_based_prompt(
                inventory_text, expiring_items, request.servings, preferences
            )
        elif recipe_type_str == "QUICK":
            # Use maxCookingTime from request (frontend), not preferences
            max_time = request.maxCookingTime
            if max_time is None:
                max_time = preferences.get('max_cooking_time', 30)
                print(f"⚠️ [PYTHON] No maxCookingTime from request, using preferences: {max_time}")
            else:
                print(f"⚡ [PYTHON] ⚡ SPEED MODE: Ultra-fast recipes under {max_time} minutes")
            return AdvancedRecipePrompts.quick_recipe_prompt(
                inventory_text, max_time, request.servings, preferences
            )
        elif recipe_type_str == "WASTAGE_PREVENTION":
            expiring_items = [item.name for item in request.expiring_items] if request.expiring_items else []
            low_stock_items = [item.name for item in request.low_stock_items] if request.low_stock_items else []
            return AdvancedRecipePrompts.wastage_prevention_prompt(
                inventory_text, low_stock_items, expiring_items, request.servings
            )
        else:  # REGULAR with personalization
            return AdvancedRecipePrompts.personalized_prompt(
                inventory_text, request.servings, preferences
            )
    
    def _parse_ai_response(self, content: str) -> Dict:
        print(f"🔍 [PYTHON] Starting JSON parsing...")
        print(f"📝 [PYTHON] Original content length: {len(content)}")
        
        original_content = content
        
        # Check if response contains multiple JSON blocks
        if content.count('"recipes"') > 1:
            print(f"🔍 [PYTHON] Multiple JSON blocks detected, combining...")
            return self._combine_multiple_json_blocks(content)
        
        # Single JSON block processing
        # Remove markdown code blocks
        if '```json' in content:
            content = content.split('```json')[1]
        if '```' in content:
            content = content.split('```')[0]
        
        # Remove any text before first {
        start = content.find('{')
        if start > 0:
            content = content[start:]
        
        # Remove any text after last }
        end = content.rfind('}') + 1
        if end > 0:
            content = content[:end]
        
        content = content.strip()
        
        print(f"📝 [PYTHON] Cleaned content length: {len(content)}")
        print(f"📝 [PYTHON] First 200 chars: {content[:200]}")
        
        if not content or not content.startswith('{'):
            print(f"❌ [PYTHON] No valid JSON structure found")
            return self._extract_recipe_manually(original_content)
        
        try:
            result = json.loads(content)
            print(f"✅ [PYTHON] JSON parsed successfully")
            return result
        except json.JSONDecodeError as e:
            print(f"❌ [PYTHON] JSON parsing failed: {e}")
            return self._extract_recipe_manually(original_content)
    
    def _combine_multiple_json_blocks(self, content: str) -> Dict:
        """Combine multiple JSON blocks into single response"""
        print(f"🔧 [PYTHON] Combining multiple JSON blocks...")
        
        import re
        all_recipes = []
        
        # Extract all JSON blocks that contain recipes
        json_blocks = re.findall(r'\{[^{}]*"recipes"\s*:\s*\[[^\]]*\][^{}]*\}', content, re.DOTALL)
        
        for i, block in enumerate(json_blocks):
            try:
                # Clean the block
                block = block.strip()
                
                # Parse the block
                parsed = json.loads(block)
                if 'recipes' in parsed and isinstance(parsed['recipes'], list):
                    all_recipes.extend(parsed['recipes'])
                    print(f"✅ [PYTHON] Block {i+1}: Added {len(parsed['recipes'])} recipes")
            except Exception as e:
                print(f"❌ [PYTHON] Block {i+1} failed: {e}")
                continue
        
        # If no recipes found, try more aggressive extraction
        if not all_recipes:
            print(f"🔧 [PYTHON] Trying aggressive extraction...")
            
            # Find all complete recipe objects
            recipe_pattern = r'\{\s*"recipe_name"\s*:\s*"[^"]+"\s*,\s*"inventory_items_used"\s*:\s*\[[^\]]*\]\s*,\s*"missing_items"\s*:\s*\[[^\]]*\]\s*,\s*"steps"\s*:\s*\[[^\]]*\]\s*\}'
            recipe_matches = re.findall(recipe_pattern, content, re.DOTALL)
            
            for match in recipe_matches:
                try:
                    recipe = json.loads(match)
                    all_recipes.append(recipe)
                    print(f"✅ [PYTHON] Extracted recipe: {recipe.get('recipe_name', 'Unknown')}")
                except Exception as e:
                    print(f"❌ [PYTHON] Failed to parse recipe: {e}")
                    continue
        
        if not all_recipes:
            print(f"❌ [PYTHON] No recipes found, using manual extraction")
            return self._extract_recipe_manually(content)
        
        print(f"✅ [PYTHON] Combined {len(all_recipes)} recipes from multiple blocks")
        return {"recipes": all_recipes}

    def _fix_json_issues(self, content: str) -> str:
        # Fix common JSON issues more aggressively
        import re
        
        print(f"🔧 [PYTHON] Attempting to fix JSON issues...")
        
        # Remove trailing commas before closing brackets
        content = re.sub(r',\s*([}\]])', r'\1', content)
        
        # Fix unescaped quotes in strings (more careful approach)
        content = re.sub(r'"([^"]*?)"([^":,}\]\s\n])', r'"\1\\"\2', content)
        
        # Ensure proper string quoting for keys
        content = re.sub(r'([{,\[]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', content)
        
        # Fix single quotes to double quotes
        content = re.sub(r"'([^']*?)'", r'"\1"', content)
        
        # Remove any control characters
        content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content)
        
        print(f"🔧 [PYTHON] Fixed content preview: {content[:200]}")
        return content
    
    def _extract_recipe_manually(self, content: str) -> Dict:
        """Manually extract recipe information when JSON parsing fails"""
        print(f"🔧 [PYTHON] Manual recipe extraction from content...")
        
        # Create a basic recipe structure
        recipes = []
        
        # Try to find recipe names (look for common patterns)
        import re
        recipe_patterns = [
            r'Recipe \d+: ([^\n]+)',
            r'"recipe_name"\s*:\s*"([^"]+)"',
            r'Name: ([^\n]+)',
        ]
        
        recipe_names = []
        for pattern in recipe_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            recipe_names.extend(matches)
        
        # If no names found, create generic ones
        if not recipe_names:
            recipe_names = ["Quick Recipe 1", "Quick Recipe 2", "Quick Recipe 3", "Quick Recipe 4"]
        
        # Ensure we have at least 4 recipes
        while len(recipe_names) < 4:
            recipe_names.append(f"Simple Recipe {len(recipe_names) + 1}")
        
        # Create single fallback recipe
        recipe = {
            "recipe_name": "This is fallback recipe",
            "inventory_items_used": [
                {"name": "Maggi", "quantity": "200", "unit": "gm"},
                {"name": "Ginger", "quantity": "20", "unit": "gm"}
            ],
            "missing_items": [
                {"name": "Salt", "quantity": "5", "unit": "gm"}
            ],
            "steps": [
                "This is a fallback recipe",
                "Use available ingredients",
                "Cook as needed"
            ]
        }
        recipes.append(recipe)
        
        print(f"✅ [PYTHON] Manual extraction created {len(recipes)} recipes")
        return {"recipes": recipes}
    
    def _convert_to_advanced_recipes(self, recipes_data: Dict, request: AdvancedRecipeRequest) -> List[AdvancedRecipe]:
        converted_recipes = []
        preferences = self._extract_preferences(request)
        
        for i, recipe_data in enumerate(recipes_data.get('recipes', [])):
            # Convert ingredients with detailed quantities
            ingredients = []
            for item in recipe_data.get('inventory_items_used', []):
                if isinstance(item, dict):
                    name = str(item.get('name', '')).strip()
                    quantity = str(item.get('quantity', '')).strip()
                    unit = str(item.get('unit', '')).strip()
                    ingredients.append(f"{name}: {quantity} {unit}")
                else:
                    ingredients.append(str(item).strip())
            
            # Convert missing items
            missing_items = []
            for item in recipe_data.get('missing_items', []):
                if isinstance(item, dict):
                    name = str(item.get('name', '')).strip()
                    quantity = str(item.get('quantity', '')).strip()
                    unit = str(item.get('unit', '')).strip()
                    missing_items.append(f"{name}: {quantity} {unit}")
                else:
                    missing_items.append(str(item).strip())
            
            # Calculate cooking time based on recipe type
            print(f"🕐 [PYTHON] Calculating time for recipe {i+1}, type: {request.recipe_type}")
            print(f"🕐 [PYTHON] Request maxCookingTime: {request.maxCookingTime}")
            print(f"🕐 [PYTHON] Preferences max_cooking_time: {preferences.get('max_cooking_time')}")
            base_time = self._calculate_cooking_time(request.recipe_type, preferences, i, request.maxCookingTime)
            print(f"🕐 [PYTHON] Calculated time for recipe {i+1}: {base_time} mins")
            
            recipe = AdvancedRecipe(
                name=recipe_data.get('recipe_name', f'Recipe {i+1}'),
                ingredients=ingredients,
                missing_items=missing_items,
                steps=recipe_data.get('steps', []),
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
        # Use request max_cooking_time if provided, otherwise use preferences
        max_time = request_max_time or preferences.get('max_cooking_time', 45)
        
        if str(recipe_type) == "QUICK" or recipe_type == RecipeType.QUICK:
            # For quick recipes, use the actual max_time from frontend
            time_per_recipe = max_time // 4  # Divide max time by 4 recipes
            calculated_time = max(5, min(time_per_recipe + (index * 2), max_time))
            print(f"⚡ [PYTHON] Quick recipe {index+1}: using max_time={max_time}, calculated={calculated_time}")
            return calculated_time
        
        # For other recipe types, respect max_time but use reasonable defaults
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
        
        # Add skill-based tips
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
    
    def _create_fallback_advanced_recipes(self, request: AdvancedRecipeRequest) -> AdvancedRecipeResponse:
        print(f"🔄 [PYTHON] Creating single fallback recipe")
        
        try:
            preferences = self._extract_preferences(request)
        except Exception:
            preferences = {
                'skill_level': 'INTERMEDIATE',
                'spice_level': 'MEDIUM'
            }
        
        # Calculate appropriate cooking time for fallback
        max_time = request.maxCookingTime or 30
        if str(request.recipe_type) == "QUICK":
            cooking_time = min(max_time, 20)
        else:
            cooking_time = 25
        
        recipe = AdvancedRecipe(
            name="This is fallback recipe",
            ingredients=[f"{item.name}: {item.quantity} {item.unit}" for item in request.items[:2]],
            missing_items=["Salt: 5 g"],
            steps=[
                "This is a fallback recipe",
                "Use available ingredients",
                "Cook as needed"
            ],
            servings=request.servings,
            cooking_time=f"{cooking_time} mins",
            difficulty_level=preferences['skill_level'],
            recipe_type=str(request.recipe_type),
            cuisine_type="Indian",
            spice_level=preferences['spice_level'],
            tips=["This is a fallback recipe when AI fails"]
        )
        
        from app.models.advanced_recipe import AdvancedRecipeResponse
        return AdvancedRecipeResponse(
            recipes=[recipe],
            recipe_type=str(request.recipe_type),
            total_recipes=1,
            expiring_items_used=self._get_expiring_items_used(request),
            wastage_prevented=False
        )