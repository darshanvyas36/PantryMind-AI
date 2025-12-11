# app/config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Server Configuration
    app_name: str = "PantryMind OCR AI Service"
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False
    
    # AI Model Configuration
    gemini_api_key: str
    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"
    
    # OCR Configuration
    max_image_size_mb: int = 10
    supported_formats: list = ["jpg", "jpeg", "png", "webp"]
    
    # Request Timeouts
    llm_timeout_seconds: int = 30
    ocr_timeout_seconds: int = 15
    
    # Java Backend Integration
    java_backend_url: Optional[str] = None
    api_key_header: str = "X-API-Key"
    internal_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env
        env_prefix = ""  # No prefix for environment variables

settings = Settings()
