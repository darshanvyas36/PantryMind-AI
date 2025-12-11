from groq import Groq
import json
import os
from dotenv import load_dotenv
from app.models.recipe import RecipeRequest, RecipeResponse, Recipe
from app.core.llm.prompts.category_recipe_prompts import CategoryRecipePrompts
from app.core.llm.prompts.search_recipe_prompts import SearchRecipePrompts

load_dotenv()

class RecipeService:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.temperature = float(os.getenv("GROQ_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("GROQ_MAX_TOKENS", "4000"))
        self.recipe_count = int(os.getenv("RECIPE_COUNT", "4"))
        self.base_cooking_time = int(os.getenv("BASE_COOKING_TIME", "20"))
        self.time_increment = int(os.getenv("TIME_INCREMENT", "5"))
        self.fallback_cooking_time = int(os.getenv("FALLBACK_COOKING_TIME", "15"))
    
    def generate_recipes(self, request: RecipeRequest, category: str = None) -> RecipeResponse:
        # Create inventory summary
        inventory_summary = []
        for item in request.items:
            unit = self._standardize_unit(item.unit, item.quantity)
            inventory_summary.append(f"- {item.name}: {unit['quantity']} {unit['unit']}")
        
        inventory_text = "\n".join(inventory_summary)
        available_items = [item.name for item in request.items]
        
        # Use category-specific prompt (category is always provided)
        if not category:
            raise ValueError("Category is required for recipe generation")
            
        print(f"🏷️ [PYTHON] Using category-specific prompt for: {category}")
        prompt = CategoryRecipePrompts.category_recipes_prompt(
            category=category,
            inventory_text=inventory_text,
            available_items=available_items,
            servings=request.servings
        )
        
        try:
            print(f"🤖 [PYTHON] Calling Groq AI for {request.servings} people" + (f" - {category} recipes" if category else "..."))
            print(f"📝 [PYTHON] FULL PROMPT SENT TO AI:")
            print(f"{'='*80}")
            print(prompt)
            print(f"{'='*80}\n")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            content = response.choices[0].message.content.strip()
            
            print(f"🤖 [PYTHON] Groq Response length: {len(content)} chars")
            print(f"\n📤 [PYTHON] RAW AI RESPONSE:")
            print(f"{'='*80}")
            print(content)
            print(f"{'='*80}\n")
            
            # Clean response
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Remove comments and clean JSON
            import re
            # Remove single line comments (// comment)
            content = re.sub(r'//.*?\n', '\n', content)
            # Remove multi-line comments (/* comment */)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            # Remove trailing commas
            content = re.sub(r',\s*}', '}', content)
            content = re.sub(r',\s*]', ']', content)
            
            # Find JSON boundaries
            start = content.find('{')
            end = content.rfind('}') + 1
            
            if start == -1 or end == 0:
                raise ValueError("No valid JSON found in response")
                
            json_content = content[start:end]
            print(f"🧹 [PYTHON] CLEANED JSON:")
            print(json_content)
            print(f"{'='*40}\n")
            
            data = json.loads(json_content)
            
            print(f"✅ [PYTHON] Successfully parsed {len(data.get('recipes', []))} recipes" + (f" for {category}" if category else ""))
            print(f"📊 [PYTHON] PARSED JSON DATA:")
            print(json.dumps(data, indent=2))
            print(f"{'='*80}\n")
            
            # Convert to our response format
            converted_recipes = []
            available_item_names = [item.name.lower().strip() for item in request.items]
            
            for i, recipe_data in enumerate(data.get('recipes', [])):
                # Convert inventory_items_used to ingredients format
                ingredients = []
                for item in recipe_data.get('inventory_items_used', []):
                    name = str(item.get('name', '')).strip()
                    quantity = str(item.get('quantity', '')).strip()
                    unit = str(item.get('unit', '')).strip()
                    
                    # Extract numeric value from quantity string
                    try:
                        import re
                        qty_match = re.search(r'([0-9.]+)', quantity)
                        if qty_match:
                            qty = float(qty_match.group(1))
                        else:
                            qty = 1
                        
                        standardized = self._standardize_unit_output(unit, qty)
                        final_qty = self._apply_minimum_quantity(standardized['quantity'], standardized['unit'])
                        ingredients.append(f"{name}: {final_qty} {standardized['unit']}")
                    except Exception as e:
                        quantity_unit = f"{quantity}{unit}".replace('gg', 'g').replace('mlml', 'ml').replace('pcspcs', 'pcs')
                        ingredients.append(f"{name}: {quantity_unit}")
                
                # Convert missing_items format and filter out inventory items
                missing_items = []
                common_items = ['water', 'ice', 'air', 'steam']
                
                for item in recipe_data.get('missing_items', []):
                    name = str(item.get('name', '')).strip()
                    quantity = str(item.get('quantity', '')).strip()
                    unit = str(item.get('unit', '')).strip()
                    
                    if name.lower() in available_item_names or name.lower() in common_items:
                        continue
                    
                    try:
                        import re
                        qty_match = re.search(r'([0-9.]+)', quantity)
                        if qty_match:
                            qty = float(qty_match.group(1))
                        else:
                            qty = 1
                        
                        standardized = self._standardize_unit_output(unit, qty)
                        final_qty = self._apply_minimum_quantity(standardized['quantity'], standardized['unit'])
                        missing_items.append(f"{name}: {final_qty} {standardized['unit']}")
                    except Exception as e:
                        quantity_unit = f"{quantity}{unit}".replace('gg', 'g').replace('mlml', 'ml').replace('pcspcs', 'pcs')
                        missing_items.append(f"{name}: {quantity_unit}")
                
                converted_recipe = Recipe(
                    name=recipe_data.get('recipe_name', f'Recipe {i+1}'),
                    ingredients=ingredients,
                    missing_items=missing_items,
                    steps=recipe_data.get('steps', []),
                    servings=request.servings,
                    cooking_time=f"{self.base_cooking_time + i*self.time_increment} mins"
                )
                converted_recipes.append(converted_recipe)
            
            return RecipeResponse(recipes=converted_recipes)
            
        except Exception as e:
            print(f"❌ [PYTHON] Error with Groq AI: {e}")
            return self._create_fallback_recipes(request.servings, request.items)
    
    def _standardize_unit(self, unit, quantity):
        """Convert units to standard format and adjust quantities"""
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
    
    def _standardize_unit_output(self, unit, quantity):
        """Standardize unit output format"""
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
    
    def _apply_minimum_quantity(self, quantity, unit):
        """Apply minimum quantity rules"""
        if unit == 'g':
            return max(5, int(quantity))  # Minimum 5g
        elif unit == 'ml':
            return max(15, int(quantity))  # Minimum 15ml
        elif unit == 'pcs':
            return max(1, int(quantity))  # Minimum 1 piece
        else:
            return int(quantity)
    
    def _create_fallback_recipes(self, servings: int, available_items) -> RecipeResponse:
        print(f"🔄 [PYTHON] Creating single sample recipe for {servings} servings")
        
        ingredients = []
        for item in available_items[:3]:  # Use only first 3 items
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
    
    def generate_recipe_by_name(self, request) -> RecipeResponse:
        """Generate recipe by specific name"""
        print(f"🍳 [PYTHON] Generating recipe by name: {request.recipeName}")
        
        # Create inventory summary
        inventory_summary = []
        for item in request.availableItems:
            inventory_summary.append(f"- {item['name']}: {item['quantity']} {item['unit']}")
        
        inventory_text = "\n".join(inventory_summary)
        
        # Use search recipe prompt
        prompt = SearchRecipePrompts.search_recipe_prompt(
            recipe_name=request.recipeName,
            inventory_text=inventory_text,
            servings=request.servings
        )
        
        try:
            print(f"📝 [PYTHON] FULL PROMPT FOR {request.recipeName}:")
            print(f"{'='*80}")
            print(prompt)
            print(f"{'='*80}\n")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            content = response.choices[0].message.content.strip()
            
            print(f"🤖 [PYTHON] AI Response for {request.recipeName}:")
            print(f"\n📤 [PYTHON] RAW AI RESPONSE:")
            print(f"{'='*80}")
            print(content)
            print(f"{'='*80}\n")
            
            # Clean and parse response
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Remove comments and clean JSON
            import re
            # Remove single line comments (// comment)
            content = re.sub(r'//.*?\n', '\n', content)
            # Remove multi-line comments (/* comment */)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            # Remove trailing commas
            content = re.sub(r',\s*}', '}', content)
            content = re.sub(r',\s*]', ']', content)
            
            start = content.find('{')
            end = content.rfind('}') + 1
            
            if start == -1 or end == 0:
                raise ValueError("No valid JSON found in response")
                
            json_content = content[start:end]
            print(f"🧹 [PYTHON] CLEANED JSON:")
            print(json_content)
            print(f"{'='*40}\n")
            
            data = json.loads(json_content)
            
            print(f"📊 [PYTHON] PARSED JSON FOR {request.recipeName}:")
            print(json.dumps(data, indent=2))
            print(f"{'='*80}\n")
            
            # Convert to response format
            converted_recipes = []
            available_item_names = [item['name'].lower().strip() for item in request.availableItems]
            

            
            for recipe_data in data.get('recipes', []):
                # Convert inventory_items_used to ingredients format
                ingredients = []
                for item in recipe_data.get('inventory_items_used', []):
                    name = str(item.get('name', '')).strip()
                    quantity = str(item.get('quantity', '')).strip()
                    unit = str(item.get('unit', '')).strip()
                    
                    try:
                        import re
                        qty_match = re.search(r'([0-9.]+)', quantity)
                        if qty_match:
                            qty = float(qty_match.group(1))
                        else:
                            qty = 1
                        
                        standardized = self._standardize_unit_output(unit, qty)
                        final_qty = self._apply_minimum_quantity(standardized['quantity'], standardized['unit'])
                        ingredients.append(f"{name}: {final_qty} {standardized['unit']}")
                    except Exception as e:
                        quantity_unit = f"{quantity}{unit}".replace('gg', 'g').replace('mlml', 'ml').replace('pcspcs', 'pcs')
                        ingredients.append(f"{name}: {quantity_unit}")
                
                # Convert missing_items format
                missing_items = []
                for item in recipe_data.get('missing_items', []):
                    name = str(item.get('name', '')).strip()
                    quantity = str(item.get('quantity', '')).strip()
                    unit = str(item.get('unit', '')).strip()
                    
                    try:
                        import re
                        qty_match = re.search(r'([0-9.]+)', quantity)
                        if qty_match:
                            qty = float(qty_match.group(1))
                        else:
                            qty = 1
                        
                        standardized = self._standardize_unit_output(unit, qty)
                        final_qty = self._apply_minimum_quantity(standardized['quantity'], standardized['unit'])
                        missing_items.append(f"{name}: {final_qty} {standardized['unit']}")
                    except Exception as e:
                        quantity_unit = f"{quantity}{unit}".replace('gg', 'g').replace('mlml', 'ml').replace('pcspcs', 'pcs')
                        missing_items.append(f"{name}: {quantity_unit}")
                
                print(f"\n🍳 [PYTHON] FINAL RECIPE SUMMARY:")
                print(f"   Recipe: {recipe_data.get('recipe_name', request.recipeName)}")
                print(f"   Ingredients ({len(ingredients)}): {ingredients}")
                print(f"   Missing Items ({len(missing_items)}): {missing_items}")
                print(f"{'='*40}\n")
                
                recipe = Recipe(
                    name=recipe_data.get('recipe_name', request.recipeName),
                    ingredients=ingredients,
                    missing_items=missing_items,
                    steps=recipe_data.get('steps', []),
                    servings=request.servings,
                    cooking_time="30 mins"
                )
                converted_recipes.append(recipe)
            
            return RecipeResponse(recipes=converted_recipes)
            
        except Exception as e:
            print(f"❌ [PYTHON] Error generating recipe by name: {e}")
            # Return single default recipe
            recipe = Recipe(
                name=f"Default Recipe - {request.recipeName}",
                ingredients=["Basic ingredients"],
                missing_items=["Check recipe online"],
                steps=["Search for recipe online"],
                servings=request.servings,
                cooking_time="30 mins"
            )
            return RecipeResponse(recipes=[recipe])