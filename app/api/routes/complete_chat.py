# app/api/routes/complete_chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ...core.agents.function_calling_agent import FunctionCallingAgent
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/complete-chat", tags=["Complete Chat"])

class CompleteChatRequest(BaseModel):
    message: str
    kitchen_id: int
    user_email: str
    context: Optional[str] = None

class CompleteChatResponse(BaseModel):
    response: str
    action_taken: Optional[str] = None
    success: bool = True
    error: Optional[str] = None

# Initialize the complete agent
complete_agent = FunctionCallingAgent()

@router.post("/", response_model=CompleteChatResponse)
async def complete_chat(request: CompleteChatRequest):
    """Complete agentic chat with full PantryMind access"""
    
    try:
        logger.info(f"Complete chat request: {request.message}")
        
        # Process the request with complete agent
        result = await complete_agent.process_request(
            user_message=request.message,
            kitchen_id=request.kitchen_id,
            user_email=request.user_email
        )
        
        return CompleteChatResponse(
            response=result["response"],
            action_taken=result.get("action_taken"),
            success=True
        )
        
    except Exception as e:
        logger.error(f"Complete chat error: {str(e)}")
        return CompleteChatResponse(
            response="I encountered an error processing your request. Please try again.",
            success=False,
            error=str(e)
        )

@router.get("/health")
async def health_check():
    """Health check for complete chat service"""
    return {"status": "healthy", "service": "complete_chat"}