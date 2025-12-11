# app/core/llm/client.py
import time
import asyncio
import hashlib
from typing import Optional, Dict, Any
import google.generativeai as genai
from app.config.settings import settings
from app.utils.exceptions import LLMError
import logging

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.timeout = 30.0
        self.last_request_time = 0
        self.min_request_interval = 0.1
        
        # Response cache
        self.response_cache: Dict[str, str] = {}
        self.cache_ttl = 3600  # 1 hour
        self.cache_timestamps: Dict[str, float] = {}
        
        genai.configure(api_key=self.api_key)
        # Use working model
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    def _get_cache_key(self, prompt: str, image_hash: str = None) -> str:
        """Generate cache key for request"""
        content = f"{prompt}_{image_hash or ''}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached response is still valid"""
        if cache_key not in self.cache_timestamps:
            return False
        return (time.time() - self.cache_timestamps[cache_key]) < self.cache_ttl
    
    def _get_image_hash(self, image_base64: str) -> str:
        """Generate hash for image to use in caching"""
        return hashlib.md5(image_base64.encode()).hexdigest()[:16]
    
    async def text_completion(
        self, 
        prompt: str, 
        model: str = None,
        max_tokens: int = 2000,
        temperature: float = 0.1
    ) -> str:
        """Send text-only completion with caching"""
        
        cache_key = self._get_cache_key(prompt)
        
        # Check cache first
        if cache_key in self.response_cache and self._is_cache_valid(cache_key):
            logger.info(f"Cache hit for text completion")
            return self.response_cache[cache_key]
        
        response = await self._generate_with_retry(prompt, max_tokens, temperature)
        
        # Cache response
        self.response_cache[cache_key] = response
        self.cache_timestamps[cache_key] = time.time()
        
        return response

    async def vision_completion(
        self,
        text_prompt: str,
        image_base64: str,
        model: str = None
    ) -> str:
        """Send vision completion with caching"""
        
        image_hash = self._get_image_hash(image_base64)
        cache_key = self._get_cache_key(text_prompt, image_hash)
        
        # Check cache first
        if cache_key in self.response_cache and self._is_cache_valid(cache_key):
            logger.info(f"Cache hit for vision completion")
            return self.response_cache[cache_key]
        
        import base64
        from PIL import Image
        import io
        
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        response = await self._generate_vision_content(text_prompt, image, 2000, 0.1)
        
        # Cache response
        self.response_cache[cache_key] = response
        self.cache_timestamps[cache_key] = time.time()
        
        return response

    async def _generate_with_retry(
        self, 
        content,
        max_tokens: int = 2000,
        temperature: float = 0.1,
        max_retries: int = 1
    ) -> str:
        """Generate content with minimal retry"""
        
        try:
            return await self._generate_content(content, max_tokens, temperature)
        except Exception as e:
            logger.error(f"Gemini error: {str(e)}")
            raise LLMError("GEMINI_ERROR", f"Gemini API error: {str(e)}")
    
    async def _generate_content(
        self, 
        content,
        max_tokens: int = 2000,
        temperature: float = 0.1
    ) -> str:
        """Internal method for text content generation"""
        
        request_start = time.time()
        
        try:
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    content, 
                    generation_config=generation_config
                )
            )
            
            total_time = (time.time() - request_start) * 1000
            logger.info(f"Gemini text completed in {total_time:.0f}ms")
            logger.info(f"Gemini response: {response.text[:200]}...")
            
            return response.text
            
        except Exception as e:
            total_time = (time.time() - request_start) * 1000
            logger.error(f"Gemini text error after {total_time:.0f}ms: {str(e)}")
            raise LLMError("GEMINI_FAILURE", f"Gemini API error: {str(e)}")

    async def _generate_vision_content(
        self, 
        text_prompt: str,
        image,
        max_tokens: int = 2000,
        temperature: float = 0.1
    ) -> str:
        """Internal method for vision content generation"""
        
        request_start = time.time()
        
        try:
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
            
            # Configure safety settings for receipts
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    [text_prompt, image],
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
            )
            
            total_time = (time.time() - request_start) * 1000
            logger.info(f"Gemini vision completed in {total_time:.0f}ms")
            logger.info(f"Gemini vision response: {response.text[:500]}...")
            
            return response.text
            
        except Exception as e:
            total_time = (time.time() - request_start) * 1000
            logger.error(f"Gemini vision error after {total_time:.0f}ms: {str(e)}")
            raise LLMError("GEMINI_FAILURE", f"Gemini vision API error: {str(e)}")
    
    def clear_cache(self):
        """Clear response cache"""
        self.response_cache.clear()
        self.cache_timestamps.clear()
        logger.info("LLM response cache cleared")

# Global client instance
llm_client = GeminiClient()
