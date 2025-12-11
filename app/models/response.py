# app/models/response.py - add new field
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from .common import ExtractedItem, DocumentType, ErrorResponse

class OCRResponse(BaseModel):
    request_id: str
    document_type: DocumentType
    raw_ocr_text: str
    items: List[ExtractedItem]
    confidence_summary: float
    processing_time_ms: int
    timestamp: datetime = Field(default_factory=datetime.now)
    message: Optional[str] = None  # Add this field for user messages

class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
