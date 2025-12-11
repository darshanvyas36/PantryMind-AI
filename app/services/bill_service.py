# app/services/bill_service.py
import uuid
import base64
import asyncio
from typing import List, Tuple
from app.core.vision.preprocessor import minimal_vision_preprocessing
from app.core.llm.client import llm_client
from app.core.llm.prompts import BillPrompts
from app.core.llm.parser import llm_parser
from app.services.enrichment_service import enrichment_service
from app.models.common import ExtractedItem, DocumentType
from app.models.response import OCRResponse
from app.utils.exceptions import OCRServiceError
from app.utils.timing import PerformanceTimer
import logging
logger = logging.getLogger(__name__)

class BillService:
    def __init__(self):
        self._metadata_cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes

    async def _get_cached_metadata(self) -> Tuple[List[dict], List[dict], List[dict]]:
        """Get cached categories, units, and locations"""
        import time
        current_time = time.time()
        
        if (self._metadata_cache is None or 
            (current_time - self._cache_timestamp) > self._cache_ttl):
            
            categories_task = enrichment_service._get_categories()
            units_task = enrichment_service._get_units()
            locations_task = enrichment_service._get_locations()
            categories, units, locations = await asyncio.gather(categories_task, units_task, locations_task)
            
            self._metadata_cache = (categories, units, locations)
            self._cache_timestamp = current_time
            logger.info("Metadata cache refreshed")
        
        return self._metadata_cache    
   
    # async def _get_cached_metadata(self) -> Tuple[List[dict], List[dict], List[dict]]:
    #     """Get cached categories, units, and locations"""
    #     import time
    #     current_time = time.time()
        
    #     if (self._metadata_cache is None or 
    #         (current_time - self._cache_timestamp) > self._cache_ttl):
            
    #         categories_task = enrichment_service._get_categories()
    #         units_task = enrichment_service._get_units()
    #         locations_task = enrichment_service._get_locations()
    #         categories, units, locations = await asyncio.gather(categories_task, units_task, locations_task)
            
    #         self._metadata_cache = (categories, units, locations)
    #         self._cache_timestamp = current_time
    #         logger.info("Metadata cache refreshed")
        
    #     return self._metadata_cache

    async def process_bill(self, image_data: bytes, filename: str, locale: str = "en-IN", timezone: str = "Asia/Kolkata") -> OCRResponse:
        request_id = str(uuid.uuid4())
        timer = PerformanceTimer(request_id)
        
        try:
            logger.info(f"Processing bill {request_id}")
            
            # Parallel preprocessing with minimal image processing
            with timer.time_step("parallel_preprocessing"):
                metadata_task = self._get_cached_metadata()
                image_task = minimal_vision_preprocessing(image_data, filename)
                (categories, units, locations), processed_image = await asyncio.gather(metadata_task, image_task)
            
            # Vision processing
            with timer.time_step("vision_processing"):
                image_base64 = base64.b64encode(processed_image).decode('utf-8')
                prompt = BillPrompts.vision_extraction(locale, categories, units, locations)
                llm_response = await llm_client.vision_completion(prompt, image_base64)
                
            with timer.time_step("response_parsing"):
                items = llm_parser.parse_bill_response(llm_response)
                
            confidence_summary = self._calculate_confidence_summary(items)
            processing_time = int(timer.get_total_time())
            timer.log_summary()
                
            logger.info(f"Bill {request_id} processed: {len(items)} items in {processing_time}ms")
                
            return OCRResponse(
                    request_id=request_id,
                    document_type=DocumentType.BILL,
                    raw_ocr_text="Vision-based processing",
                    items=items,
                    confidence_summary=confidence_summary,
                    processing_time_ms=processing_time,
                    message=self._generate_user_message(items, confidence_summary)
                )
                
        except Exception as e:
                timer.log_summary()
                logger.error(f"Bill processing failed for {request_id}: {str(e)}")
                raise OCRServiceError("PROCESSING_FAILED", f"Failed to process bill: {str(e)}")
        
    def _calculate_confidence_summary(self, items: List[ExtractedItem]) -> float:
            if not items:
                return 0.0
            total_confidence = sum(item.confidence for item in items)
            return round(total_confidence / len(items), 2)
        
    def _generate_user_message(self, items: List[ExtractedItem], confidence: float) -> str:
            if not items:
                return "No food items detected. Please ensure it's a clear grocery receipt."
            elif confidence < 0.5:
                return f"Found {len(items)} items with low confidence. Consider clearer image."
            elif confidence < 0.7:
                return f"Extracted {len(items)} items. Some may need verification."
            else:
                return f"Successfully extracted {len(items)} food items from receipt."

bill_service = BillService()
