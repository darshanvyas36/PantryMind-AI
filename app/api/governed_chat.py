# app/api/governed_chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..agents.smart_pantry_agent import SmartPantryAgent
from ..config.settings import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    kitchen_id: int = 1
    user_email: str = "guest@example.com"

class ChatResponse(BaseModel):
    response: str
    metadata: Optional[dict] = None

# Initialize the smart LLM-powered pantry agent
agent_system = SmartPantryAgent(java_backend_url=settings.java_backend_url)

@router.post("/governed-chat/", response_model=ChatResponse)
async def governed_chat(request: ChatRequest):
    """
    Process user message through the governed agent system
    """
    try:
        logger.info(f"Processing governed chat request: {request.message[:100]}...")
        
        # Process through state machine
        response = agent_system.process_message(
            message=request.message,
            kitchen_id=request.kitchen_id,
            user_email=request.user_email
        )
        
        return ChatResponse(
            response=response,
            metadata={
                "system": "smart_llm_agent",
                "version": "1.0",
                "llm_powered": True
            }
        )
        
    except Exception as e:
        logger.error(f"Error in governed chat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Governed chat processing failed: {str(e)}"
        )

@router.get("/system-status/")
async def system_status():
    """
    Get status of the governed agent system
    """
    return {
        "status": "operational",
        "agents": {
            "governor": "active",
            "intent": "active", 
            "planner": "active",
            "inventory": "active",
            "ocr": "active",
            "recipe": "active",
            "validator": "active",
            "responder": "active"
        },
        "state_machine": "ready",
        "version": "1.0"
    }