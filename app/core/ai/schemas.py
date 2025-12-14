# app/core/ai/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

class ExtractedItemSchema(BaseModel):
    raw_name: str = Field(..., description="Original item name")
    canonical_name: str = Field(..., description="Standardized name")
    category: str = Field(..., description="Item category")
    brand: Optional[str] = Field(None, description="Brand name")
    quantity: Optional[float] = Field(None, description="Quantity")
    unit: Optional[str] = Field(None, description="Unit")
    price: Optional[float] = Field(None, description="Price")
    shelf_life_days: Optional[int] = Field(None, description="Shelf life days")
    storage_type: Optional[str] = Field(None, description="Storage location")
    is_food: bool = Field(True, description="Is food item")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence")

class BillExtractionSchema(BaseModel):
    items: List[ExtractedItemSchema] = Field(..., description="Extracted items")

class ProductDetectionSchema(BaseModel):
    products: List[ExtractedItemSchema] = Field(..., description="Detected products")

class LabelExtractionSchema(BaseModel):
    product_name: str = Field(..., description="Product name")
    canonical_name: str = Field(..., description="Standardized name")
    brand: Optional[str] = Field(None, description="Brand")
    category: str = Field(..., description="Category")
    quantity: Optional[float] = Field(None, description="Quantity")
    unit: Optional[str] = Field(None, description="Unit")
    expiry_date: Optional[str] = Field(None, description="Expiry YYYY-MM-DD")
    shelf_life_days: Optional[int] = Field(None, description="Shelf life days")
    storage_type: str = Field(..., description="Storage type")
    is_food: bool = Field(True, description="Is food")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence")

class RecipeItemSchema(BaseModel):
    name: str = Field(..., description="Item name")
    quantity: str = Field(..., description="Quantity with unit")
    unit: str = Field(..., description="Unit")

class RecipeSchema(BaseModel):
    recipe_name: str = Field(..., description="Recipe name")
    inventory_items_used: List[RecipeItemSchema] = Field(..., description="Items used")
    missing_items: List[RecipeItemSchema] = Field(..., description="Missing items")
    steps: List[str] = Field(..., description="Cooking steps")

class RecipeGenerationSchema(BaseModel):
    recipes: List[RecipeSchema] = Field(..., description="Generated recipes")

class ShoppingSuggestionSchema(BaseModel):
    name: str = Field(..., description="Item name")
    quantity: float = Field(..., description="Suggested quantity")
    unit: str = Field(..., description="Unit")
    reason: str = Field(..., description="Reason for suggestion")
    priority: str = Field(..., description="Priority level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence")

class ShoppingSuggestionsSchema(BaseModel):
    suggestions: List[ShoppingSuggestionSchema] = Field(..., description="Shopping suggestions")