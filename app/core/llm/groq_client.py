# app/core/llm/groq_client.py
import time
from typing import Optional
from groq import AsyncGroq
from app.config.settings import settings
from app.utils.exceptions import LLMError
import logging

logger = logging.getLogger(__name__)

class GroqRecipeClient:
    def __init__(self):
        self.api_key = settings.groq_api_key
        self.client = AsyncGroq(api_key=self.api_key)
        self.model = settings.groq_model
    
    async def text_completion(
        self, 
        prompt: str, 
        max_tokens: int = 4000,
        temperature: float = 0.7,
        timeout_seconds: int = 15
    ) -> str:
        """Send text completion request to Groq with 8 second timeout"""
        
        import asyncio
        
        start_time = time.time()
        print(f"🚀 [GROQ] Starting recipe generation with {timeout_seconds}s timeout")
        
        try:
            # Create the API call task
            api_task = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Wait for completion with timeout
            response = await asyncio.wait_for(api_task, timeout=timeout_seconds)
            
            total_time = (time.time() - start_time) * 1000
            print(f"✅ [GROQ] Recipe generated successfully in {total_time:.0f}ms")
            logger.info(f"Groq recipe completed in {total_time:.0f}ms")
            
            return response.choices[0].message.content
            
        except asyncio.TimeoutError:
            total_time = (time.time() - start_time) * 1000
            print(f"⏰ [GROQ] Timeout after {total_time:.0f}ms - switching to fallback")
            raise LLMError("GROQ_TIMEOUT", f"Recipe generation timed out after {timeout_seconds} seconds")
            
        except Exception as e:
            total_time = (time.time() - start_time) * 1000
            print(f"❌ [GROQ] Error after {total_time:.0f}ms: {str(e)}")
            logger.error(f"Groq recipe error after {total_time:.0f}ms: {str(e)}")
            raise LLMError("GROQ_FAILURE", f"Groq API error: {str(e)}")

# Global recipe client instance  
try:
    groq_recipe_client = GroqRecipeClient()
    print(f"✅ [GROQ] Client initialized with model: {groq_recipe_client.model}")
except Exception as e:
    print(f"❌ [GROQ] Client initialization failed: {e}")
    groq_recipe_client = None