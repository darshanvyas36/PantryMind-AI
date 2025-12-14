# app/agents/planner_agent.py
from typing import Dict, Any, List
from .base import BaseAgent, AgentResult

class PlannerAgent(BaseAgent):
    def __init__(self, model_name: str = "qwen-2.5-14b-instruct"):
        super().__init__("PlannerAgent", model_name)
        
    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        intent = input_data.get("intent")
        message = input_data.get("message", "")
        
        plan_templates = {
            "inventory": self._plan_inventory,
            "recipe": self._plan_recipe,
            "ocr": self._plan_ocr,
            "analytics": self._plan_analytics,
            "greeting": self._plan_greeting,
            "help": self._plan_help
        }
        
        planner = plan_templates.get(intent, self._plan_help)
        steps = planner(message, input_data)
        
        return AgentResult(
            success=True,
            data={
                "plan_steps": steps,
                "total_steps": len(steps),
                "estimated_time": len(steps) * 2  # 2 seconds per step
            },
            confidence=0.9,
            metadata={"planner_type": intent}
        )
    
    def _plan_inventory(self, message: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["add", "create", "new"]):
            return [{
                "step": 1,
                "tool_type": "inventory",
                "operation": "create",
                "description": "Add new inventory item"
            }]
        elif any(word in message_lower for word in ["update", "change", "modify"]):
            return [{
                "step": 1,
                "tool_type": "inventory",
                "operation": "update",
                "description": "Update inventory item"
            }]
        elif any(word in message_lower for word in ["delete", "remove"]):
            return [{
                "step": 1,
                "tool_type": "inventory",
                "operation": "delete",
                "description": "Delete inventory item"
            }]
        else:
            return [{
                "step": 1,
                "tool_type": "inventory",
                "operation": "read",
                "description": "Get inventory information"
            }]
    
    def _plan_recipe(self, message: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {
                "step": 1,
                "tool_type": "inventory",
                "operation": "read",
                "description": "Get available ingredients"
            },
            {
                "step": 2,
                "tool_type": "recipe",
                "operation": "generate",
                "description": "Generate recipe suggestions"
            }
        ]
    
    def _plan_ocr(self, message: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {
                "step": 1,
                "tool_type": "ocr",
                "operation": "process",
                "description": "Process receipt image"
            },
            {
                "step": 2,
                "tool_type": "inventory",
                "operation": "bulk_add",
                "description": "Add extracted items to inventory"
            }
        ]
    
    def _plan_analytics(self, message: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{
            "step": 1,
            "tool_type": "analytics",
            "operation": "generate_report",
            "description": "Generate analytics report"
        }]
    
    def _plan_greeting(self, message: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{
            "step": 1,
            "tool_type": "greeting",
            "operation": "greet_user",
            "description": "Greet the user"
        }]
    
    def _plan_help(self, message: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{
            "step": 1,
            "tool_type": "help",
            "operation": "provide_guidance",
            "description": "Provide help information"
        }]
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "input_schema": {
                "intent": {"type": "string", "required": True},
                "message": {"type": "string", "required": True}
            },
            "output_schema": {
                "plan_steps": {"type": "array", "items": {"type": "object"}},
                "total_steps": {"type": "integer", "minimum": 1, "maximum": 5}
            },
            "preconditions": ["intent must be valid"],
            "side_effects": []
        }