# app/agents/gemini_agent.py
from typing import Dict, Any
import requests
import json
from ..config.settings import settings

class GeminiAgent:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
        
    def chat(self, system_prompt: str, user_message: str, temperature: float = 0.1) -> str:
        """Make a chat completion request to Gemini"""
        
        try:
            # Combine system prompt and user message for Gemini
            combined_prompt = f"{system_prompt}\n\nUser: {user_message}\nAssistant:"
            
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{
                        "parts": [{"text": combined_prompt}]
                    }],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": 1000
                    }
                },
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["candidates"][0]["content"]["parts"][0]["text"].strip()
            else:
                print(f"Gemini API error: {response.status_code}")
                print(f"Response: {response.text}")
                return ""
                
        except Exception as e:
            print(f"Gemini request error: {e}")
            return ""