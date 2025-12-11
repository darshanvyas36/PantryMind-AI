# app/services/product_service.py
import uuid
import base64
from typing import List
from app.core.vision.preprocessor import minimal_vision_preprocessing
from app.core.llm.client import llm_client
from app.core.llm.prompts import ProductPrompts
from app.core.llm.parser import llm_parser
from app.models.common import ExtractedItem, DocumentType
from app.models.response import OCRResponse
from app.utils.exceptions import OCRServiceError
from app.utils.timing import PerformanceTimer
import logging

logger = logging.getLogger(__name__)

class ProductService:
    
    async def process_product(
        self, 
        image_data: bytes, 
        filename: str,
        mode: str = "auto"
    ) -> OCRResponse:
        """Process product/shelf image using vision model"""
        
        request_id = str(uuid.uuid4())
        timer = PerformanceTimer(request_id)
        
        try:
            logger.info(f"Processing product {request_id} in {mode} mode")
            
            with timer.time_step("image_preprocessing"):
                processed_image = await minimal_vision_preprocessing(image_data, filename)
            
            with timer.time_step("vision_processing"):
                image_base64 = base64.b64encode(processed_image).decode('utf-8')
                
                if mode == "single":
                    prompt = ProductPrompts.single_detection()
                else:
                    prompt = ProductPrompts.multi_detection()
                
                llm_response = await llm_client.vision_completion(prompt, image_base64)
            
            with timer.time_step("response_parsing"):
                items = llm_parser.parse_product_response(llm_response)
                confidence_summary = self._calculate_confidence_summary(items)
            
            processing_time = int(timer.get_total_time())
            timer.log_summary()
            
            logger.info(f"Product {request_id} processed: {len(items)} items in {processing_time}ms")
            
            return OCRResponse(
                request_id=request_id,
                document_type=DocumentType.PRODUCT,
                raw_ocr_text="Vision-based detection",
                items=items,
                confidence_summary=confidence_summary,
                processing_time_ms=processing_time,
                message=self._generate_user_message(items, mode, confidence_summary)
            )
            
        except Exception as e:
            timer.log_summary()
            logger.error(f"Product processing failed: {str(e)}")
            raise OCRServiceError("PROCESSING_FAILED", f"Failed to process product: {str(e)}")
    
    def _calculate_confidence_summary(self, items: List[ExtractedItem]) -> float:
        if not items:
            return 0.0
        return round(sum(item.confidence for item in items) / len(items), 2)
    
    def _generate_user_message(self, items: List[ExtractedItem], mode: str, confidence: float) -> str:
        if not items:
            return "No products detected. Ensure clear, well-lit image."
        elif confidence < 0.4:
            return f"Detected {len(items)} products with poor quality. Upload clearer image."
        else:
            return f"Successfully detected {len(items)} products."

product_service = ProductService()
