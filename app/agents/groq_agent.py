# app/agents/groq_agent.py
from typing import Dict, Any
import requests
import json
from ..config.settings import settings

class GroqAgent:
    def __init__(self):
        self.api_key = settings.groq_api_key
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        
    def chat(self, system_prompt: str, user_message: str, temperature: float = 0.1) -> str:
        """Make a chat completion request to Groq"""
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": temperature,
                    "max_tokens": 1000
                },
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"Groq API error: {response.status_code}")
                return ""
                
        except Exception as e:
            print(f"Groq request error: {e}")
            return ""