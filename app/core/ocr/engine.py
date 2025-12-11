# app/core/ocr/engine.py
import pytesseract
import cv2
import numpy as np
from PIL import Image
import io
from typing import Tuple, Optional
from app.utils.exceptions import OCRError
import logging
import time

logger = logging.getLogger(__name__)

class OCREngine:
    def __init__(self):
        # Simplified config for speed
        self.config = '--oem 3 --psm 6'
    
    async def extract_text(self, image_data: bytes) -> str:
        """Extract text from image using OCR"""
        start_time = time.time()
        
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Minimal preprocessing for speed
            processed_image = self._fast_preprocess(image)
            
            # Extract text using Tesseract
            ocr_start = time.time()
            text = pytesseract.image_to_string(processed_image, config=self.config)
            ocr_time = (time.time() - ocr_start) * 1000
            logger.info(f"Tesseract OCR took {ocr_time:.0f}ms")
            
            # Clean text
            cleaned_text = self._clean_text(text)
            
            total_time = (time.time() - start_time) * 1000
            logger.info(f"Total OCR: {total_time:.0f}ms, extracted {len(cleaned_text)} chars")
            
            return cleaned_text
            
        except Exception as e:
            total_time = (time.time() - start_time) * 1000
            logger.error(f"OCR failed after {total_time:.0f}ms: {str(e)}")
            raise OCRError("OCR_EXTRACTION_FAILED", f"Failed to extract text: {str(e)}")
    
    def _fast_preprocess(self, image: Image.Image) -> Image.Image:
        """Minimal preprocessing for speed"""
        try:
            # Convert to grayscale only
            if image.mode != 'L':
                image = image.convert('L')
            return image
        except Exception:
            return image
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ""
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)

# Global OCR engine instance
ocr_engine = OCREngine()
