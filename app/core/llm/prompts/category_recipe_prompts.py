# app/core/llm/category_recipe_prompts.py
from typing import List

class CategoryRecipePrompts:
    
    @staticmethod
    def category_recipes_prompt(category: str, inventory_text: str, available_items: List[str], servings: int) -> str:
        return f"""You are an expert recipe generator.
Generate 4 different {category} recipes based strictly on the user's inventory.

========================================
INVENTORY DATA (Important):
{inventory_text}

TARGET SERVINGS: {servings}
CATEGORY: {category}
========================================

### CRITICAL RULES FOR ALL 4 {category.upper()} RECIPES

1. **CATEGORY FOCUS**
   - ALL 4 recipes MUST be {category} recipes
   - Sweet Treats: desserts, sweets, puddings, cookies, cakes
   - Spicy Food: hot, spicy, chili-based dishes
   - Breakfast: morning meals, cereals, toast, eggs
   - Lunch: midday meals, rice dishes, curries
   - Dinner: evening meals, hearty dishes
   - Salads: fresh, raw or lightly cooked vegetables
   - Seasonal: weather-appropriate dishes

2. **INVENTORY ITEMS USAGE**
   - Available items: {', '.join(available_items)}
   - Calculate realistic quantities for {servings} person(s)
   - If inventory item is used, it MUST go in "inventory_items_used" ONLY
   - NEVER put inventory items in "missing_items"

3. **MISSING INGREDIENTS**
   - Only add items NOT in inventory: {', '.join(available_items)}
   - Use realistic quantities for {servings} person(s)
   - Focus on ingredients that match the {category} theme

4. **UNITS ALLOWED**
   - g (grams)
   - ml (milliliters)
   - pcs (pieces)

5. **OUTPUT RULES**
   - Valid JSON only
   - No explanations
   - 4 different {category} recipes with authentic names
   - Focus on {category} cooking techniques
   - Realistic cooking quantities

### RETURN EXACTLY IN THIS JSON FORMAT:

{{
  "recipes": [
    {{
      "recipe_name": "{category} Recipe 1",
      "inventory_items_used": [
        {{ "name": "", "quantity": "", "unit": "" }}
      ],
      "missing_items": [
        {{ "name": "", "quantity": "", "unit": "" }}
      ],
      "steps": [
        "Step 1 ...",
        "Step 2 ...",
        "Step 3 ...",
        "Step 4 ...",
        "Step 5 ..."
      ]
    }},
    {{
      "recipe_name": "{category} Recipe 2",
      "inventory_items_used": [],
      "missing_items": [],
      "steps": []
    }},
    {{
      "recipe_name": "{category} Recipe 3",
      "inventory_items_used": [],
      "missing_items": [],
      "steps": []
    }},
    {{
      "recipe_name": "{category} Recipe 4",
      "inventory_items_used": [],
      "missing_items": [],
      "steps": []
    }}
  ]
}}"""