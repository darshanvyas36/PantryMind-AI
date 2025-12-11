# app/api/routes/ocr.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Optional
from app.services.bill_service import bill_service
from app.services.label_service import label_service
from app.services.product_service import product_service
from app.models.response import OCRResponse, ErrorResponse
from app.utils.exceptions import OCRServiceError
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ocr", tags=["OCR"])

@router.post("/bill", response_model=OCRResponse)
async def process_bill(
    image: UploadFile = File(..., description="Bill image file"),
    locale: str = Form("en-IN", description="Locale for processing"),
    timezone: str = Form("Asia/Kolkata", description="Timezone for date processing")
):
    """Process bill image and extract grocery items"""
    try:
        # Validate file
        if not image.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read image data
        image_data = await image.read()
        
        # Process bill
        result = await bill_service.process_bill(
            image_data=image_data,
            filename=image.filename,
            locale=locale,
            timezone=timezone
        )
        
        return result
        
    except OCRServiceError as e:
        logger.error(f"OCR service error: {e.error_code} - {e.message}")
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
                debug_info=e.debug_info
            ).dict()
        )
    except Exception as e:
        logger.error(f"Unexpected error in bill processing: {str(e)}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="Internal server error"
            ).dict()
        )

@router.post("/label", response_model=OCRResponse)
async def process_label(
    image: UploadFile = File(..., description="Product label image"),
    storage_hint: Optional[str] = Form(None, description="Storage type hint")
):
    """Process product label and extract information"""
    try:
        if not image.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        image_data = await image.read()
        
        result = await label_service.process_label(
            image_data=image_data,
            filename=image.filename,
            storage_hint=storage_hint
        )
        
        return result
        
    except OCRServiceError as e:
        logger.error(f"OCR service error: {e.error_code} - {e.message}")
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
                debug_info=e.debug_info
            ).dict()
        )
    except Exception as e:
        logger.error(f"Unexpected error in label processing: {str(e)}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="Internal server error"
            ).dict()
        )

@router.post("/product", response_model=OCRResponse)
async def process_product(
    image: UploadFile = File(..., description="Product or shelf image"),
    mode: str = Form("auto", description="Processing mode: single, shelf, or auto")
):
    """Process product image and detect items"""
    try:
        if not image.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        image_data = await image.read()
        
        result = await product_service.process_product(
            image_data=image_data,
            filename=image.filename,
            mode=mode
        )
        
        return result
        
    except OCRServiceError as e:
        logger.error(f"OCR service error: {e.error_code} - {e.message}")
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
                debug_info=e.debug_info
            ).dict()
        )
    except Exception as e:
        logger.error(f"Unexpected error in product processing: {str(e)}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="Internal server error"
            ).dict()
        )
