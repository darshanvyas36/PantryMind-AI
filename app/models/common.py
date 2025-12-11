# app/models/common.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

class DocumentType(str, Enum):
    BILL = "bill"
    LABEL = "label" 
    PRODUCT = "product"
    SHELF = "shelf"

class StorageType(str, Enum):
    PANTRY = "pantry"
    FRIDGE = "fridge"
    FREEZER = "freezer"
    UNKNOWN = "unknown"

class ExtractedItem(BaseModel):
    raw_name: str
    canonical_name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    location: Optional[str] = None  # Add location field
    price: Optional[float] = None
    expiry_date: Optional[date] = None
    expiry_source: Optional[str] = None
    storage_type: StorageType = StorageType.UNKNOWN
    is_food: Optional[bool] = None
    brand: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    bounding_box: Optional[List[float]] = None


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    debug_info: Optional[str] = None
