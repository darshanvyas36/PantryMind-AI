# app/services/label_service.py
import uuid
import base64
from app.core.vision.preprocessor import minimal_vision_preprocessing
from app.models.common import DocumentType
from app.models.response import OCRResponse
from app.utils.exceptions import OCRServiceError
from app.utils.timing import PerformanceTimer
import logging
logger = logging.getLogger(__name__)

class LabelService:
    
    async def process_label(
        self, 
        image_data: bytes, 
        filename: str,
        storage_hint: str = None
    ) -> OCRResponse:
        """Process product label using vision model"""
        
        request_id = str(uuid.uuid4())
        timer = PerformanceTimer(request_id)
        
        try:
            logger.info(f"Processing label {request_id}")
            
            with timer.time_step("image_preprocessing"):
                processed_image = await minimal_vision_preprocessing(image_data, filename)
            
            with timer.time_step("ai_processing"):
                image_base64 = base64.b64encode(processed_image).decode('utf-8')
                
                from app.core.ai.pipeline import ai_pipeline
                from app.core.ai.converter import schema_converter
                
                schema_result = await ai_pipeline.process_label(image_base64)
                item = schema_converter.label_schema_to_item(schema_result)
            
            processing_time = int(timer.get_total_time())
            timer.log_summary()
            
            return OCRResponse(
                request_id=request_id,
                document_type=DocumentType.LABEL,
                raw_ocr_text="Vision-based processing",
                items=[item],
                confidence_summary=item.confidence,
                processing_time_ms=processing_time,
                message="Successfully extracted product information from label."
            )
            
        except Exception as e:
            timer.log_summary()
            logger.error(f"Label processing failed: {str(e)}")
            raise OCRServiceError("PROCESSING_FAILED", f"Failed to process label: {str(e)}")

label_service = LabelService()
