# app/services/label_service.py
import uuid
import base64
from app.core.vision.preprocessor import minimal_vision_preprocessing
from app.core.llm.client import llm_client
from app.core.llm.prompts import LabelPrompts
from app.core.llm.parser import llm_parser
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
            
            with timer.time_step("vision_processing"):
                image_base64 = base64.b64encode(processed_image).decode('utf-8')
                prompt = LabelPrompts.vision_extraction()
                llm_response = await llm_client.vision_completion(prompt, image_base64)
            
            with timer.time_step("response_parsing"):
                item = llm_parser.parse_label_response(llm_response)
            
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
