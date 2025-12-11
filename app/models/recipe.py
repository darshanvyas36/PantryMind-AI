from pydantic import BaseModel
from typing import List

class InventoryItem(BaseModel):
    name: str
    quantity: int
    unit: str

class RecipeRequest(BaseModel):
    items: List[InventoryItem]
    servings: int = 4  # Default to 4 servings

class Recipe(BaseModel):
    name: str
    ingredients: List[str]
    missing_items: List[str]
    steps: List[str]
    servings: int
    cooking_time: str

class RecipeResponse(BaseModel):
    recipes: List[Recipe]  # Return multiple recipes