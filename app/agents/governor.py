# app/agents/governor.py
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel
import json

class AgentRole(Enum):
    INTENT = "intent"
    PLANNER = "planner"
    INVENTORY = "inventory"
    OCR = "ocr"
    RECIPE = "recipe"
    VALIDATOR = "validator"
    RESPONDER = "responder"

class ExecutionState(Enum):
    INTENT = "intent"
    PLAN = "plan"
    EXECUTE = "execute"
    VALIDATE = "validate"
    RESPOND = "respond"
    ERROR = "error"

class AgentDecision(BaseModel):
    allowed_agent: AgentRole
    state: ExecutionState
    confidence: float
    reasoning: str
    preconditions_met: bool
    reject_reason: Optional[str] = None

class Governor:
    def __init__(self):
        self.rules = {
            "ocr_confidence_threshold": 0.8,
            "inventory_write_requires_validation": True,
            "recipe_agent_readonly": True,
            "max_plan_steps": 5,
            "require_intent_confidence": 0.7
        }
        
    def decide_next_agent(self, current_state: ExecutionState, context: Dict[str, Any]) -> AgentDecision:
        """Single source of truth for agent routing"""
        
        if current_state == ExecutionState.INTENT:
            return self._route_from_intent(context)
        elif current_state == ExecutionState.PLAN:
            return self._route_from_plan(context)
        elif current_state == ExecutionState.EXECUTE:
            return self._route_from_execute(context)
        elif current_state == ExecutionState.VALIDATE:
            return self._route_from_validate(context)
        else:
            return AgentDecision(
                allowed_agent=AgentRole.RESPONDER,
                state=ExecutionState.RESPOND,
                confidence=1.0,
                reasoning="Default to response",
                preconditions_met=True
            )
    
    def _route_from_intent(self, context: Dict[str, Any]) -> AgentDecision:
        intent_confidence = context.get("intent_confidence", 0.0)
        
        if intent_confidence < self.rules["require_intent_confidence"]:
            return AgentDecision(
                allowed_agent=AgentRole.RESPONDER,
                state=ExecutionState.RESPOND,
                confidence=1.0,
                reasoning="Intent unclear, need clarification",
                preconditions_met=False,
                reject_reason="Low intent confidence"
            )
        
        return AgentDecision(
            allowed_agent=AgentRole.PLANNER,
            state=ExecutionState.PLAN,
            confidence=0.9,
            reasoning="Intent clear, proceed to planning",
            preconditions_met=True
        )
    
    def _route_from_plan(self, context: Dict[str, Any]) -> AgentDecision:
        plan_steps = context.get("plan_steps", [])
        
        if len(plan_steps) > self.rules["max_plan_steps"]:
            return AgentDecision(
                allowed_agent=AgentRole.RESPONDER,
                state=ExecutionState.RESPOND,
                confidence=1.0,
                reasoning="Plan too complex",
                preconditions_met=False,
                reject_reason="Exceeds max plan steps"
            )
        
        # Route to first tool agent based on plan
        first_step = plan_steps[0] if plan_steps else {}
        tool_type = first_step.get("tool_type")
        
        # Direct response for greeting and help
        if tool_type in ["greeting", "help"]:
            return AgentDecision(
                allowed_agent=AgentRole.RESPONDER,
                state=ExecutionState.RESPOND,
                confidence=1.0,
                reasoning=f"Direct response for {tool_type}",
                preconditions_met=True
            )
        
        agent_map = {
            "inventory": AgentRole.INVENTORY,
            "ocr": AgentRole.OCR,
            "recipe": AgentRole.RECIPE
        }
        
        agent = agent_map.get(tool_type, AgentRole.RESPONDER)
        
        return AgentDecision(
            allowed_agent=agent,
            state=ExecutionState.EXECUTE,
            confidence=0.85,
            reasoning=f"Execute {tool_type} step",
            preconditions_met=True
        )
    
    def _route_from_execute(self, context: Dict[str, Any]) -> AgentDecision:
        execution_result = context.get("execution_result", {})
        confidence = execution_result.get("confidence", 0.0)
        
        # OCR specific validation
        if context.get("current_agent") == AgentRole.OCR:
            if confidence < self.rules["ocr_confidence_threshold"]:
                return AgentDecision(
                    allowed_agent=AgentRole.VALIDATOR,
                    state=ExecutionState.VALIDATE,
                    confidence=1.0,
                    reasoning="OCR confidence too low, needs validation",
                    preconditions_met=True
                )
        
        # Inventory write validation
        if (context.get("current_agent") == AgentRole.INVENTORY and 
            context.get("operation_type") == "write" and
            self.rules["inventory_write_requires_validation"]):
            return AgentDecision(
                allowed_agent=AgentRole.VALIDATOR,
                state=ExecutionState.VALIDATE,
                confidence=1.0,
                reasoning="Inventory write requires validation",
                preconditions_met=True
            )
        
        return AgentDecision(
            allowed_agent=AgentRole.RESPONDER,
            state=ExecutionState.RESPOND,
            confidence=0.9,
            reasoning="Execution successful, ready to respond",
            preconditions_met=True
        )
    
    def _route_from_validate(self, context: Dict[str, Any]) -> AgentDecision:
        validation_result = context.get("validation_result", {})
        is_valid = validation_result.get("is_valid", False)
        
        if not is_valid:
            return AgentDecision(
                allowed_agent=AgentRole.RESPONDER,
                state=ExecutionState.ERROR,
                confidence=1.0,
                reasoning="Validation failed",
                preconditions_met=False,
                reject_reason=validation_result.get("error_reason", "Validation failed")
            )
        
        return AgentDecision(
            allowed_agent=AgentRole.RESPONDER,
            state=ExecutionState.RESPOND,
            confidence=1.0,
            reasoning="Validation passed, ready to respond",
            preconditions_met=True
        )
    
    def validate_tool_preconditions(self, agent: AgentRole, tool_input: Dict[str, Any]) -> bool:
        """Validate tool preconditions before execution"""
        
        if agent == AgentRole.INVENTORY:
            return self._validate_inventory_preconditions(tool_input)
        elif agent == AgentRole.OCR:
            return self._validate_ocr_preconditions(tool_input)
        elif agent == AgentRole.RECIPE:
            return self._validate_recipe_preconditions(tool_input)
        
        return True
    
    def _validate_inventory_preconditions(self, tool_input: Dict[str, Any]) -> bool:
        if tool_input.get("operation") == "update":
            quantity = tool_input.get("quantity", 0)
            if quantity < 0:
                return False
            if not tool_input.get("canonical_item_id"):
                return False
        return True
    
    def _validate_ocr_preconditions(self, tool_input: Dict[str, Any]) -> bool:
        image_data = tool_input.get("image_data")
        if not image_data:
            return False
        return True
    
    def _validate_recipe_preconditions(self, tool_input: Dict[str, Any]) -> bool:
        # Recipe agent is read-only
        if tool_input.get("operation") in ["create", "update", "delete"]:
            return False
        return True