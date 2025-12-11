# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import ocr, health, ai_shopping, recipes
from app.config.settings import settings
from app.utils.exceptions import OCRServiceError
from app.utils.logger import setup_logging
import logging


# for recipes  ----
from app.api.routes import recipes, advanced_recipes

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="OCR and AI service for PantryMind inventory management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(ocr.router)
app.include_router(recipes.router)
app.include_router(ai_shopping.router, prefix="/api/ai-shopping", tags=["AI Shopping"])

# for recipes 
app.include_router(recipes.router)
app.include_router(advanced_recipes.router)

# Global exception handler
@app.exception_handler(OCRServiceError)
async def ocr_service_exception_handler(request: Request, exc: OCRServiceError):
    return JSONResponse(
        status_code=400,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "debug_info": exc.debug_info if settings.debug else None
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Debug mode: {settings.debug}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down OCR service")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
