# app/core/vision/preprocessor.py
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

async def minimal_vision_preprocessing(image_data: bytes, filename: str = None) -> bytes:
    """Minimal preprocessing for vision models"""
    try:
        image = Image.open(io.BytesIO(image_data))
        
        # Only resize if too large (vision models have limits)
        max_size = 1024
        if max(image.size) > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Save with minimal compression
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=85)
        processed_data = output.getvalue()
        
        logger.info(f"Image processed: {len(image_data)} -> {len(processed_data)} bytes")
        return processed_data
        
    except Exception as e:
        logger.error(f"Image preprocessing failed: {str(e)}")
        # Return original if preprocessing fails
        return image_data
