# app/agents/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum

class AgentResult(BaseModel):
    success: bool
    data: Dict[str, Any]
    confidence: float
    error_message: Optional[str] = None
    side_effects: list = []
    metadata: Dict[str, Any] = {}

class BaseAgent(ABC):
    def __init__(self, name: str, model_name: str):
        self.name = name
        self.model_name = model_name
        self.version = "1.0"
        
    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """Execute the agent's primary function"""
        pass
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input before execution"""
        return True
    
    def get_schema(self) -> Dict[str, Any]:
        """Return input/output schema for this agent"""
        return {
            "input_schema": {},
            "output_schema": {},
            "preconditions": [],
            "side_effects": []
        }