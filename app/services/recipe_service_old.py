from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json
from app.models.recipe import RecipeRequest, RecipeResponse, Recipe
from app.core.llm.prompts.category_recipe_prompts import CategoryRecipePrompts
from app.core.llm.prompts.search_recipe_prompts import SearchRecipePrompts
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class RecipeService:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.7,
            google_api_key=settings.gemini_api_key,
            max_output_tokens=4000
        )
        self.json_parser = JsonOutputParser()
        self.recipe_count = 4
        self.base_cooking_time = 20
        self.time_increment = 5
        self.fallback_cooking_time = 15
    
    def generate_recipes(self, request: RecipeRequest, category: str = None) -> RecipeResponse:
        # Create inventory summary
        inventory_summary = []
        for item in request.items:
            unit = self._standardize_unit(item.unit, item.quantity)
            inventory_summary.append(f"- {item.name}: {unit['quantity']} {unit['unit']}")
        
        inventory_text = "\n".join(inventory_summary)
        
        # Create LangChain prompt template
        prompt_template = ChatPromptTemplate.from_template(
            """Generate {recipe_count} recipes for {category} category using available inventory.
            
Available Inventory:
{inventory_text}
            
Servings: {servings}
            
Return JSON format:
{{
  "recipes": [
    {{
      "recipe_name": "Recipe Name",
      "inventory_items_used": [{{"name": "item", "quantity": "amount", "unit": "unit"}}],
      "missing_items": [{{"name": "item", "quantity": "amount", "unit": "unit"}}],
      "steps": ["step1", "step2"]
    }}
  ]
}}"""
        )
        
        # Create chain with JSON parser
        chain = prompt_template | self.llm | self.json_parser
        
        try:
            logger.info(f"Generating {category} recipes for {request.servings} people")
            
            # Try LangChain first, fallback to original logic if needed
            try:
                result = chain.invoke({
                    "recipe_count": self.recipe_count,
                    "category": category or "general",
                    "inventory_text": inventory_text,
                    "servings": request.servings
                })
                
                logger.info(f"Successfully generated {len(result.get('recipes', []))} recipes")
                converted_recipes = self._convert_recipes(result.get('recipes', []), request)
                return RecipeResponse(recipes=converted_recipes)
                
            except Exception as langchain_error:
                logger.warning(f"LangChain failed, using fallback: {str(langchain_error)}")
                # Use original prompt logic as fallback
                prompt = CategoryRecipePrompts.category_recipes_prompt(
                    category=category,
                    inventory_text=inventory_text,
                    available_items=[item.name for item in request.items],
                    servings=request.servings
                )
                
                # Direct LLM call as fallback
                from langchain_core.messages import HumanMessage
                response = self.llm.invoke([HumanMessage(content=prompt)])
                
                # Parse response manually if JSON parser fails
                content = response.content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                
                import re
                content = re.sub(r'//.*?\n', '\n', content)
                content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
                content = re.sub(r',\s*}', '}', content)
                content = re.sub(r',\s*]', ']', content)
                
                start = content.find('{')
                end = content.rfind('}') + 1
                if start != -1 and end != 0:
                    json_content = content[start:end]
                    data = json.loads(json_content)
                    converted_recipes = self._convert_recipes_legacy(data.get('recipes', []), request)
                    return RecipeResponse(recipes=converted_recipes)
                
                raise Exception("Both LangChain and fallback failed")
            
        except Exception as e:
            logger.error(f"Error generating recipes: {str(e)}")
            return self._create_fallback_recipes(request.servings, request.items)
    
    def _convert_recipes(self, recipes_data, request):
        """Convert AI response to Recipe objects using LangChain output"""
        converted_recipes = []
        
        for i, recipe_data in enumerate(recipes_data):
            # Process ingredients
            ingredients = []
            for item in recipe_data.get('inventory_items_used', []):
                name = str(item.get('name', '')).strip()
                quantity = str(item.get('quantity', '')).strip()
                unit = str(item.get('unit', '')).strip()
                ingredients.append(f"{name}: {quantity} {unit}")
            
            # Process missing items
            missing_items = []
            for item in recipe_data.get('missing_items', []):
                name = str(item.get('name', '')).strip()
                quantity = str(item.get('quantity', '')).strip()
                unit = str(item.get('unit', '')).strip()
                missing_items.append(f"{name}: {quantity} {unit}")
            
            recipe = Recipe(
                name=recipe_data.get('recipe_name', f'Recipe {i+1}'),
                ingredients=ingredients,
                missing_items=missing_items,
                steps=recipe_data.get('steps', []),
                servings=request.servings,
                cooking_time=f"{self.base_cooking_time + i*self.time_increment} mins"
            )
            converted_recipes.append(recipe)
        
        return converted_recipes
    
    def _convert_recipes_legacy(self, recipes_data, request):
        """Legacy recipe conversion for backward compatibility"""
        converted_recipes = []
        available_item_names = [item.name.lower().strip() for item in request.items]
        
        for i, recipe_data in enumerate(recipes_data):
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
                except Exception:
                    quantity_unit = f"{quantity}{unit}".replace('gg', 'g').replace('mlml', 'ml').replace('pcspcs', 'pcs')
                    ingredients.append(f"{name}: {quantity_unit}")
            
            # Convert missing_items format
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
                except Exception:
                    quantity_unit = f"{quantity}{unit}".replace('gg', 'g').replace('mlml', 'ml').replace('pcspcs', 'pcs')
                    missing_items.append(f"{name}: {quantity_unit}")
            
            recipe = Recipe(
                name=recipe_data.get('recipe_name', f'Recipe {i+1}'),
                ingredients=ingredients,
                missing_items=missing_items,
                steps=recipe_data.get('steps', []),
                servings=request.servings,
                cooking_time=f"{self.base_cooking_time + i*self.time_increment} mins"
            )
            converted_recipes.append(recipe)
        
        return converted_recipes
    
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
        """Generate recipe by specific name using LangChain"""
        logger.info(f"Generating recipe by name: {request.recipeName}")
        
        # Create inventory summary
        inventory_summary = []
        for item in request.availableItems:
            inventory_summary.append(f"- {item['name']}: {item['quantity']} {item['unit']}")
        
        inventory_text = "\n".join(inventory_summary)
        
        # Create LangChain prompt template
        prompt_template = ChatPromptTemplate.from_template(
            """Generate a recipe for "{recipe_name}" using available inventory.
            
Available Inventory:
{inventory_text}
            
Servings: {servings}
            
Return JSON format:
{{
  "recipes": [
    {{
      "recipe_name": "{recipe_name}",
      "inventory_items_used": [{{"name": "item", "quantity": "amount", "unit": "unit"}}],
      "missing_items": [{{"name": "item", "quantity": "amount", "unit": "unit"}}],
      "steps": ["step1", "step2"]
    }}
  ]
}}"""
        )
        
        # Create chain
        chain = prompt_template | self.llm | self.json_parser
        
        try:
            result = chain.invoke({
                "recipe_name": request.recipeName,
                "inventory_text": inventory_text,
                "servings": request.servings
            })
            
            converted_recipes = self._convert_recipes(result.get('recipes', []), request)
            return RecipeResponse(recipes=converted_recipes)
            
        except Exception as e:
            logger.error(f"Error generating recipe by name: {str(e)}")
            recipe = Recipe(
                name=f"Default Recipe - {request.recipeName}",
                ingredients=["Basic ingredients"],
                missing_items=["Check recipe online"],
                steps=["Search for recipe online"],
                servings=request.servings,
                cooking_time="30 mins"
            )
            return RecipeResponse(recipes=[recipe])