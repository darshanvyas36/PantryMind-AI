# app/core/ai/pipeline.py
import asyncio
from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from app.core.ai.schemas import (
    BillExtractionSchema, ProductDetectionSchema, LabelExtractionSchema, 
    RecipeGenerationSchema, ShoppingSuggestionsSchema, RecipeSchema, RecipeItemSchema,
    ShoppingSuggestionSchema
)
from app.core.ai.preprocessor import image_preprocessor
from app.config.settings import settings
from app.utils.exceptions import LLMError
import logging

logger = logging.getLogger(__name__)

class AIProcessingPipeline:
    """End-to-end AI pipeline: Data + Image → LLM → Structured JSON"""
    
    def __init__(self):
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.1,
            google_api_key=settings.gemini_api_key,
            max_output_tokens=2000
        )
        
        # Output parsers for each schema
        self.bill_parser = PydanticOutputParser(pydantic_object=BillExtractionSchema)
        self.product_parser = PydanticOutputParser(pydantic_object=ProductDetectionSchema)
        self.label_parser = PydanticOutputParser(pydantic_object=LabelExtractionSchema)
    
    async def process_bill(
        self, 
        image_base64: str, 
        context_data: Dict[str, Any]
    ) -> BillExtractionSchema:
        """Process bill/receipt with structured output"""
        
        # 1. Preprocess image
        processed_image = image_preprocessor.preprocess_for_llm(image_base64)
        
        # 2. Build system prompt
        system_prompt = """You are a structured data extraction assistant.
Return ONLY valid JSON matching the exact schema.
Do not explain anything."""
        
        # 3. Build context prompt
        categories = ", ".join([cat.get("name", "") for cat in context_data.get("categories", [])])
        units = ", ".join([unit.get("name", "") for unit in context_data.get("units", [])])
        locations = ", ".join([loc.get("name", "") for loc in context_data.get("locations", [])])
        
        user_prompt = f"""Extract ALL grocery items from this receipt.

Use ONLY these categories: {categories or "dairy, beverages, staples"}
Use ONLY these units: {units or "ml, litre, grams, kg, piece"}
Use ONLY these storage types: {locations or "pantry, fridge, freezer"}

PREDICT shelf_life_days based on product type:
- Milk/dairy: 7 days
- Bread/bakery: 5 days  
- Canned goods: 730 days
- Fresh vegetables: 5-14 days
- Meat: 3 days
- Frozen: 90 days

{self.bill_parser.get_format_instructions()}"""
        
        # 4. LLM call with multimodal input
        try:
            response = await self._invoke_llm(system_prompt + user_prompt, processed_image)
            
            # 5. Parse to structured output
            structured_output = self.bill_parser.parse(response.content)
            
            logger.info(f"Bill processed: {len(structured_output.items)} items extracted")
            return structured_output
            
        except Exception as e:
            logger.error(f"Bill processing failed: {e}")
            raise LLMError("BILL_PROCESSING_FAILED", str(e))
    
    async def process_product(
        self, 
        image_base64: str, 
        mode: str = "single",
        context_data: Dict[str, Any] = None
    ) -> ProductDetectionSchema:
        """Process product detection with structured output"""
        
        processed_image = image_preprocessor.preprocess_for_llm(image_base64)
        
        system_prompt = """You are a product detection assistant.
Return ONLY valid JSON matching the exact schema.
Do not explain anything."""
        
        if mode == "single":
            user_prompt = f"""Identify the main food/grocery product in this image.
PREDICT shelf_life_days based on product type.
{self.product_parser.get_format_instructions()}"""
        else:
            user_prompt = f"""Identify ALL visible food items in this image.
PREDICT shelf_life_days for each product.
{self.product_parser.get_format_instructions()}"""
        
        try:
            response = await self._invoke_llm(system_prompt + user_prompt, processed_image)
            structured_output = self.product_parser.parse(response.content)
            
            logger.info(f"Products processed: {len(structured_output.products)} items detected")
            return structured_output
            
        except Exception as e:
            logger.error(f"Product processing failed: {e}")
            raise LLMError("PRODUCT_PROCESSING_FAILED", str(e))
    
    async def process_label(
        self, 
        image_base64: str,
        context_data: Dict[str, Any] = None
    ) -> LabelExtractionSchema:
        """Process label extraction with structured output"""
        
        processed_image = image_preprocessor.preprocess_for_llm(image_base64)
        
        system_prompt = """You are a label extraction assistant.
Return ONLY valid JSON matching the exact schema.
Do not explain anything."""
        
        user_prompt = f"""Extract product information from this label.
If expiry_date is visible, extract it as YYYY-MM-DD.
If not visible, predict shelf_life_days based on product type.
{self.label_parser.get_format_instructions()}"""
        
        try:
            response = await self._invoke_llm(system_prompt + user_prompt, processed_image)
            structured_output = self.label_parser.parse(response.content)
            
            logger.info(f"Label processed: {structured_output.product_name}")
            return structured_output
            
        except Exception as e:
            logger.error(f"Label processing failed: {e}")
            raise LLMError("LABEL_PROCESSING_FAILED", str(e))
    
    async def process_recipe_generation(
        self,
        inventory_data: Dict[str, Any],
        category: str = None
    ) -> RecipeGenerationSchema:
        """Generate recipes with structured output"""
        
        system_prompt = """You are a recipe generation assistant.
Return ONLY valid JSON matching the exact schema.
Do not explain anything."""
        
        # Check for non-veg items in inventory
        inventory_text = inventory_data.get('inventory_text', '')
        has_nonveg = self._has_nonveg_items(inventory_text)
        recipe_name = inventory_data.get('recipe_name', '')
        is_nonveg_search = self._is_nonveg_search(recipe_name)
        
        # Determine dietary restriction
        if has_nonveg or is_nonveg_search:
            dietary_instruction = "You can suggest both vegetarian and non-vegetarian recipes."
        else:
            dietary_instruction = "ONLY suggest VEGETARIAN recipes. Do not include any meat, chicken, fish, or non-vegetarian ingredients."
        
        # Determine recipe count and focus based on request type
        recipe_count = 1 if recipe_name else 4
        
        if recipe_name:
            # Recipe search - single specific recipe
            focus_instruction = f"Generate 1 recipe specifically for '{recipe_name}' using available ingredients."
        else:
            # Category/general recipes - 4 recipes
            focus_instruction = f"Generate 4 diverse recipes for {category or 'general'} category using available inventory."
        
        user_prompt = f"""{focus_instruction}

Available Inventory:
{inventory_text}

Servings: {inventory_data.get('servings', 4)}

DIETARY RESTRICTION: {dietary_instruction}

QUANTITY GUIDELINES:
- Use realistic cooking portions for {inventory_data.get('servings', 4)} people
- Rice/Grains: 200-300g total (50-75g per person)
- Vegetables: 400-500g total (100-125g per person) 
- Oil: 2-3 tablespoons (30-45ml)
- Spices: 1-2 teaspoons each (5-10g)
- Onions: 2-3 medium (200-300g)
- Tomatoes: 2-3 medium (200-300g)
- Milk/Liquids: 500-750ml total
- Salt: 1-2 teaspoons (5-10g)
- Sugar: 2-4 tablespoons (30-60g)

Return JSON format:
{{
  "recipes": [
    {{
      "recipe_name": "Recipe Name",
      "inventory_items_used": [{{
        "name": "item",
        "quantity": "realistic_amount_for_servings", 
        "unit": "appropriate_unit"
      }}],
      "missing_items": [{{
        "name": "item",
        "quantity": "realistic_amount_for_servings",
        "unit": "appropriate_unit"
      }}],
      "steps": ["step1", "step2"]
    }}
  ]
}}"""
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.invoke([HumanMessage(content=system_prompt + user_prompt)])
            )
            
            # Parse JSON manually since PydanticOutputParser might fail
            import json
            content = response.content.strip()
            
            # Clean JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            
            # Find JSON object
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                json_content = content[start:end]
                data = json.loads(json_content)
                
                # Convert to schema format - limit to expected count
                recipes = []
                recipe_list = data.get('recipes', [])
                max_recipes = 1 if recipe_name else 4
                
                for recipe_data in recipe_list[:max_recipes]:
                    recipe = RecipeSchema(
                        recipe_name=recipe_data.get('recipe_name', recipe_name or 'Recipe'),
                        inventory_items_used=[
                            RecipeItemSchema(
                                name=item.get('name', ''),
                                quantity=str(item.get('quantity', '')),
                                unit=item.get('unit', '')
                            ) for item in recipe_data.get('inventory_items_used', [])
                        ],
                        missing_items=[
                            RecipeItemSchema(
                                name=item.get('name', ''),
                                quantity=str(item.get('quantity', '')),
                                unit=item.get('unit', '')
                            ) for item in recipe_data.get('missing_items', [])
                        ],
                        steps=recipe_data.get('steps', [])
                    )
                    recipes.append(recipe)
                
                structured_output = RecipeGenerationSchema(recipes=recipes)
                logger.info(f"Recipes generated: {len(structured_output.recipes)} recipes")
                return structured_output
            
            raise Exception("No valid JSON found")
            
        except Exception as e:
            logger.error(f"Recipe generation failed: {e}")
            # Return fallback based on request type with realistic quantities
            servings = inventory_data.get('servings', 4)
            if recipe_name:
                fallback_recipe = RecipeSchema(
                    recipe_name=recipe_name,
                    inventory_items_used=[
                        RecipeItemSchema(name="Rice", quantity=str(50 * servings), unit="g"),
                        RecipeItemSchema(name="Oil", quantity="30", unit="ml")
                    ],
                    missing_items=[
                        RecipeItemSchema(name="Salt", quantity="5", unit="g"),
                        RecipeItemSchema(name="Spices", quantity="10", unit="g")
                    ],
                    steps=[f"Search online for {recipe_name} recipe", "Use available ingredients", "Cook as desired"]
                )
                return RecipeGenerationSchema(recipes=[fallback_recipe])
            else:
                # 4 fallback recipes for category/general requests
                fallback_recipes = []
                base_ingredients = [
                    ("Rice", str(60 * servings), "g"),
                    ("Vegetables", str(100 * servings), "g"),
                    ("Oil", "30", "ml"),
                    ("Onion", "200", "g")
                ]
                for i in range(4):
                    fallback_recipes.append(RecipeSchema(
                        recipe_name=f"Simple Recipe {i+1}",
                        inventory_items_used=[
                            RecipeItemSchema(name=ing[0], quantity=ing[1], unit=ing[2]) 
                            for ing in base_ingredients[:2]
                        ],
                        missing_items=[
                            RecipeItemSchema(name="Salt", quantity="5", unit="g"),
                            RecipeItemSchema(name="Spices", quantity="10", unit="g")
                        ],
                        steps=["Use available ingredients", "Cook as desired", "Season to taste"]
                    ))
                return RecipeGenerationSchema(recipes=fallback_recipes)
    
    async def process_shopping_suggestions(
        self,
        inventory_data: Dict[str, Any]
    ) -> ShoppingSuggestionsSchema:
        """Generate shopping suggestions with structured output"""
        
        system_prompt = """You are a shopping suggestion assistant.
Return ONLY valid JSON matching the exact schema.
Do not explain anything."""
        
        user_prompt = f"""Analyze inventory and suggest smart shopping items:

Inventory:
{inventory_data.get('inventory_text', '')}

List Type: {inventory_data.get('list_type', 'WEEKLY')}
Existing Items: {inventory_data.get('existing_items', [])}

Return JSON format:
{{
  "suggestions": [
    {{
      "name": "item name",
      "quantity": 2.0,
      "unit": "kg",
      "reason": "Low stock",
      "priority": "high",
      "confidence": 0.9
    }}
  ]
}}"""
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.invoke([HumanMessage(content=system_prompt + user_prompt)])
            )
            
            # Parse JSON manually
            import json
            content = response.content.strip()
            
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                json_content = content[start:end]
                data = json.loads(json_content)
                
                suggestions = []
                for item in data.get('suggestions', []):
                    suggestion = ShoppingSuggestionSchema(
                        name=item.get('name', ''),
                        quantity=float(item.get('quantity', 1.0)),
                        unit=item.get('unit', 'piece'),
                        reason=item.get('reason', 'Suggested'),
                        priority=item.get('priority', 'medium'),
                        confidence=float(item.get('confidence', 0.8))
                    )
                    suggestions.append(suggestion)
                
                structured_output = ShoppingSuggestionsSchema(suggestions=suggestions)
                logger.info(f"Shopping suggestions: {len(structured_output.suggestions)} items")
                return structured_output
            
            raise Exception("No valid JSON found")
            
        except Exception as e:
            logger.error(f"Shopping suggestions failed: {e}")
            # Return fallback
            fallback_suggestion = ShoppingSuggestionSchema(
                name="Basic groceries",
                quantity=1.0,
                unit="item",
                reason="General suggestion",
                priority="medium",
                confidence=0.5
            )
            return ShoppingSuggestionsSchema(suggestions=[fallback_suggestion])
    
    def _has_nonveg_items(self, inventory_text: str) -> bool:
        """Check if inventory contains non-vegetarian items"""
        nonveg_keywords = [
            'chicken', 'mutton', 'beef', 'pork', 'fish', 'meat', 'lamb', 
            'turkey', 'duck', 'prawn', 'shrimp', 'crab', 'lobster', 'salmon',
            'tuna', 'bacon', 'ham', 'sausage', 'egg'
        ]
        inventory_lower = inventory_text.lower()
        return any(keyword in inventory_lower for keyword in nonveg_keywords)
    
    def _is_nonveg_search(self, recipe_name: str) -> bool:
        """Check if user is specifically searching for non-veg recipe"""
        if not recipe_name:
            return False
        
        nonveg_keywords = [
            'chicken', 'mutton', 'beef', 'pork', 'fish', 'meat', 'lamb',
            'turkey', 'duck', 'prawn', 'shrimp', 'crab', 'lobster', 'salmon',
            'tuna', 'bacon', 'ham', 'sausage', 'egg', 'biryani', 'curry'
        ]
        recipe_lower = recipe_name.lower()
        return any(keyword in recipe_lower for keyword in nonveg_keywords)
    
    async def _invoke_llm(self, text_prompt: str, image_base64: str) -> Any:
        """Invoke LLM with text + image input"""
        
        message = HumanMessage(
            content=[
                {"type": "text", "text": text_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
            ]
        )
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: self.model.invoke([message]))
        
        return response

# Global pipeline instance
ai_pipeline = AIProcessingPipeline()