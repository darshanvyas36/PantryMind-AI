# app/core/ai/preprocessor.py
import base64
from PIL import Image
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class ImagePreprocessor:
    """Enterprise-grade image preprocessing for LLM consumption"""
    
    @staticmethod
    def preprocess_for_llm(base64_image: str, max_size: int = 1024) -> str:
        """
        Preprocess image for optimal LLM performance
        
        Args:
            base64_image: Raw base64 encoded image
            max_size: Maximum dimension size
            
        Returns:
            Processed base64 image optimized for LLM
        """
        try:
            # Decode base64 safely
            image_bytes = base64.b64decode(base64_image)
            image = Image.open(BytesIO(image_bytes))
            
            # Convert to RGB (removes alpha channel, normalizes format)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize maintaining aspect ratio
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Enhance contrast slightly for better OCR
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.1)
            
            # Re-encode to base64 with optimization
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=85, optimize=True)
            processed_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            logger.info(f"Image preprocessed: {len(base64_image)} -> {len(processed_b64)} chars")
            return processed_b64
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            # Return original if preprocessing fails
            return base64_image

image_preprocessor = ImagePreprocessor()