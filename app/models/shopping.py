from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class InventoryItem(BaseModel):
    name: str
    quantity: float
    unit: str
    category: str
    minStock: Optional[float] = 5

class ShoppingSuggestionRequest(BaseModel):
    kitchenId: int
    inventory: List[InventoryItem]
    requestType: str = "SHOPPING_SUGGESTIONS"

class AISuggestion(BaseModel):
    itemName: str
    quantity: float
    unit: str = "pcs"
    reason: str
    priority: str = "MEDIUM"
    confidence: float
    category: str = "Other"

class ShoppingSuggestionsResponse(BaseModel):
    suggestions: List[AISuggestion]
    analysisType: str = "AI_POWERED"
    confidenceScore: float
    generatedAt: datetime

class ConsumptionAnalysisResponse(BaseModel):
    totalItems: int
    lowStockCount: int
    analysisType: str
    efficiency: float
    insights: List[str]
