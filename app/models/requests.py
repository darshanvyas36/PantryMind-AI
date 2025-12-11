# app/models/requests.py
from pydantic import BaseModel
from typing import Optional
from .common import DocumentType

class OCRRequest(BaseModel):
    document_type: DocumentType
    locale: str = "en-IN"
    timezone: str = "Asia/Kolkata"
    storage_type_hint: Optional[str] = None
    mode: Optional[str] = "auto"  # For product: "single" or "shelf"
