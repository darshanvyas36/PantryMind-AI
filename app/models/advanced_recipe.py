from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
from datetime import datetime

class SkillLevel(str, Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"

class RecipeType(str, Enum):
    REGULAR = "REGULAR"
    EXPIRY_BASED = "EXPIRY_BASED"
    QUICK = "QUICK"
    WASTAGE_PREVENTION = "WASTAGE_PREVENTION"

class SpiceLevel(str, Enum):
    MILD = "MILD"
    MEDIUM = "MEDIUM"
    SPICY = "SPICY"
    EXTRA_SPICY = "EXTRA_SPICY"

class AdvancedInventoryItem(BaseModel):
    name: str
    quantity: int
    unit: str
    expiry_date: Optional[str] = None
    is_expiring: Optional[bool] = False
    is_low_stock: Optional[bool] = False

class UserPreferences(BaseModel):
    dietary_restrictions: Optional[List[str]] = []
    cuisine_preferences: Optional[List[str]] = []
    skill_level: Optional[SkillLevel] = SkillLevel.INTERMEDIATE
    max_cooking_time: Optional[int] = 45
    spice_level: Optional[SpiceLevel] = SpiceLevel.MEDIUM
    avoid_ingredients: Optional[List[str]] = []

class AdvancedRecipeRequest(BaseModel):
    items: List[AdvancedInventoryItem]
    servings: int = 4
    user_id: Optional[int] = None
    recipe_type: Optional[RecipeType] = None
    maxCookingTime: Optional[int] = None
    preferences: Optional[UserPreferences] = None
    expiring_items: Optional[List[AdvancedInventoryItem]] = []
    low_stock_items: Optional[List[AdvancedInventoryItem]] = []

class AdvancedRecipe(BaseModel):
    name: str
    ingredients: List[str]
    missing_items: List[str]
    steps: List[str]
    servings: int
    cooking_time: str
    difficulty_level: Optional[str] = "INTERMEDIATE"
    recipe_type: Optional[str] = "REGULAR"
    cuisine_type: Optional[str] = "Indian"
    spice_level: Optional[str] = "MEDIUM"
    nutritional_info: Optional[str] = None
    tips: Optional[List[str]] = []

class AdvancedRecipeResponse(BaseModel):
    recipes: List[AdvancedRecipe]
    recipe_type: str
    total_recipes: int
    expiring_items_used: Optional[List[str]] = []
    wastage_prevented: Optional[bool] = False
    is_fallback: Optional[bool] = False
    fallback_reason: Optional[str] = None