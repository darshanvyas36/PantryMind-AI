# app/agents/state_machine.py
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field
from .governor import Governor, ExecutionState, AgentRole
from .llm_intent_agent import LLMIntentAgent
from .planner_agent import PlannerAgent
from .tool_agents import InventoryAgent, OCRAgent, RecipeAgent
from .validator_agent import ValidatorAgent
from .response_agent import ResponseAgent

@dataclass
class ExecutionContext:
    user_message: str
    kitchen_id: int
    user_email: str
    current_state: ExecutionState = ExecutionState.INTENT
    intent: Optional[str] = None
    intent_confidence: float = 0.0
    plan_steps: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    validation_results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class AgentStateMachine:
    def __init__(self, java_backend_url: str = "http://localhost:8080"):
        self.governor = Governor()
        
        # Initialize all agents
        self.agents = {
            AgentRole.INTENT: LLMIntentAgent(),
            AgentRole.PLANNER: PlannerAgent(),
            AgentRole.INVENTORY: InventoryAgent(java_backend_url=java_backend_url),
            AgentRole.OCR: OCRAgent(),
            AgentRole.RECIPE: RecipeAgent(),
            AgentRole.VALIDATOR: ValidatorAgent(),
            AgentRole.RESPONDER: ResponseAgent()
        }
        
    def process_message(self, message: str, kitchen_id: int, user_email: str) -> str:
        """Main entry point for processing user messages"""
        
        context = ExecutionContext(
            user_message=message,
            kitchen_id=kitchen_id,
            user_email=user_email
        )
        
        print(f"DEBUG: Processing message: {message}")
        
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while context.current_state != ExecutionState.RESPOND and iteration < max_iterations:
            iteration += 1
            
            # Get governor decision
            decision = self.governor.decide_next_agent(
                context.current_state,
                self._build_governor_context(context)
            )
            
            print(f"DEBUG: State: {context.current_state}, Agent: {decision.allowed_agent}, Intent: {context.intent}")
            
            # Check if action is rejected
            if not decision.preconditions_met:
                context.current_state = ExecutionState.ERROR
                context.errors.append(decision.reject_reason or "Action rejected")
                continue
            
            # Execute the decided agent
            try:
                result = self._execute_agent(decision.allowed_agent, context)
                print(f"DEBUG: Agent {decision.allowed_agent} result: {result.get('success', False)}")
                self._update_context_from_result(context, decision.allowed_agent, result)
                context.current_state = decision.state
                
            except Exception as e:
                context.current_state = ExecutionState.ERROR
                context.errors.append(str(e))
        
        # Generate final response
        if context.current_state == ExecutionState.ERROR:
            return self._generate_error_response(context)
        else:
            return self._generate_final_response(context)
    
    def _build_governor_context(self, context: ExecutionContext) -> Dict[str, Any]:
        """Build context for governor decision making"""
        return {
            "intent_confidence": context.intent_confidence,
            "plan_steps": context.plan_steps,
            "current_step": context.current_step,
            "execution_result": context.execution_results[-1] if context.execution_results else {},
            "validation_result": context.validation_results[-1] if context.validation_results else {},
            "current_agent": getattr(context, 'current_agent', None),
            "operation_type": getattr(context, 'operation_type', None)
        }
    
    def _execute_agent(self, agent_role: AgentRole, context: ExecutionContext) -> Dict[str, Any]:
        """Execute a specific agent with proper input"""
        
        agent = self.agents[agent_role]
        
        if agent_role == AgentRole.INTENT:
            input_data = {"message": context.user_message}
            
        elif agent_role == AgentRole.PLANNER:
            input_data = {
                "intent": context.intent,
                "message": context.user_message,
                "kitchen_id": context.kitchen_id
            }
            
        elif agent_role in [AgentRole.INVENTORY, AgentRole.OCR, AgentRole.RECIPE]:
            # Get current step from plan
            if context.current_step < len(context.plan_steps):
                step = context.plan_steps[context.current_step]
                input_data = {
                    "operation": step.get("operation"),
                    "kitchen_id": context.kitchen_id,
                    "user_email": context.user_email,
                    **step  # Include all step data
                }
            else:
                input_data = {"kitchen_id": context.kitchen_id}
                
        elif agent_role == AgentRole.VALIDATOR:
            # Determine what to validate based on last execution
            last_result = context.execution_results[-1] if context.execution_results else {}
            input_data = {
                "validation_type": "ocr_result" if "extracted_items" in last_result else "inventory_write",
                "data": last_result
            }
            
        elif agent_role == AgentRole.RESPONDER:
            input_data = {
                "execution_state": "error" if context.errors else "success",
                "context": {
                    "intent": context.intent,
                    "execution_results": context.execution_results,
                    "error_reason": context.errors[-1] if context.errors else None,
                    "plan_steps": context.plan_steps
                }
            }
        else:
            input_data = {}
        
        # Validate preconditions before execution
        if not self.governor.validate_tool_preconditions(agent_role, input_data):
            raise Exception(f"Preconditions not met for {agent_role.value}")
        
        # Execute agent
        result = agent.execute(input_data)
        
        return {
            "agent": agent_role.value,
            "success": result.success,
            "data": result.data,
            "confidence": result.confidence,
            "error_message": result.error_message,
            "side_effects": result.side_effects,
            "metadata": result.metadata
        }
    
    def _update_context_from_result(self, context: ExecutionContext, agent_role: AgentRole, result: Dict[str, Any]):
        """Update execution context based on agent result"""
        
        if not result["success"]:
            context.errors.append(result.get("error_message", "Agent execution failed"))
            return
        
        data = result["data"]
        
        if agent_role == AgentRole.INTENT:
            context.intent = data.get("intent")
            context.intent_confidence = data.get("confidence", 0.0)
            
        elif agent_role == AgentRole.PLANNER:
            context.plan_steps = data.get("plan_steps", [])
            context.current_step = 0
            
        elif agent_role in [AgentRole.INVENTORY, AgentRole.OCR, AgentRole.RECIPE]:
            context.execution_results.append(result)
            context.current_step += 1
            
        elif agent_role == AgentRole.VALIDATOR:
            context.validation_results.append(result)
            if not data.get("is_valid", True):
                context.errors.extend(data.get("errors", []))
        
        # Store metadata
        context.metadata[f"{agent_role.value}_result"] = result
    
    def _generate_error_response(self, context: ExecutionContext) -> str:
        """Generate error response"""
        error_agent = self.agents[AgentRole.RESPONDER]
        result = error_agent.execute({
            "execution_state": "error",
            "context": {"error_reason": context.errors[-1] if context.errors else "Unknown error"}
        })
        return result.data.get("response", "Sorry, something went wrong.")
    
    def _generate_final_response(self, context: ExecutionContext) -> str:
        """Generate final successful response"""
        response_agent = self.agents[AgentRole.RESPONDER]
        result = response_agent.execute({
            "execution_state": "success",
            "context": {
                "intent": context.intent,
                "execution_results": context.execution_results,
                "plan_steps": context.plan_steps
            }
        })
        print(f"DEBUG: Final response intent: {context.intent}, plan_steps: {context.plan_steps}")
        return result.data.get("response", "Task completed successfully!")