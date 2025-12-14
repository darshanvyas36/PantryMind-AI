# app/core/tools/base_tool.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx
import logging
from app.config.settings import settings

logger = logging.getLogger(__name__)

class BaseTool(ABC):
    """Base class for all PantryMind tools"""
    
    def __init__(self):
        self.java_api_base = settings.java_backend_url
        self.timeout = 5.0
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description"""
        pass
    
    @abstractmethod
    async def _run(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool"""
        pass
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """Run tool with error handling"""
        try:
            return await self._run(**kwargs)
        except Exception as e:
            logger.error(f"Tool {self.name} error: {str(e)}")
            return {"error": f"Tool execution failed: {str(e)}"}
    
    async def _make_api_call(self, endpoint: str, params: Optional[Dict] = None, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP call to Java backend"""
        url = f"{self.java_api_base}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if method == "GET":
                response = await client.get(url, params=params or {})
            elif method == "POST":
                response = await client.post(url, json=data or {}, params=params or {})
            elif method == "PUT":
                response = await client.put(url, json=data or {}, params=params or {})
            elif method == "DELETE":
                response = await client.delete(url, params=params or {})
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}