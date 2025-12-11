# app/api/routes/health.py
from fastapi import APIRouter
from app.models.response import HealthResponse
from app.config.settings import settings

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy")

@router.get("/")
async def root():
    """Root endpoint"""
    return {"message": f"Welcome to {settings.app_name}"}
