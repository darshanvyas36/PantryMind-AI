# app/api/routes/chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_core.output_parsers import PydanticOutputParser
from app.core.agents.base_agent import PantryMindChatbot
from app.core.agents.tool_agent import PantryMindToolAgent
from app.core.agents.agentic_agent import AgenticAgent
from app.core.agents.fully_agentic_agent import FullyAgenticAgent
from app.core.agents.service_agent import ServiceAgent
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    kitchen_id: int = 1  # Default kitchen ID
    use_tools: bool = True  # Enable tools by default
    agentic_mode: bool = True  # Enable full agentic capabilities
    fully_agentic: bool = True  # Enable COMPLETE autonomous capabilities

class ChatResponse(BaseModel):
    response: str
    phase: str
    confidence: float = 0.8
    tools_used: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "response": "I can help you with pantry management!",
                "phase": "intelligent_assistant",
                "confidence": 0.9,
                "tools_used": True
            }
        }

# Initialize agents
basic_chatbot = PantryMindChatbot()
tool_agent = PantryMindToolAgent()
agentic_agent = AgenticAgent()
fully_agentic_agent = FullyAgenticAgent()
service_agent = ServiceAgent()
response_parser = PydanticOutputParser(pydantic_object=ChatResponse)

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Determine which agent to use based on capabilities needed
        if request.fully_agentic:
            # Use service agent with direct Java service calls
            response_text = await service_agent.chat_async(
                request.message, request.session_id, request.kitchen_id
            )
            phase = "service_agent"
            tools_used = True
        elif request.agentic_mode:
            # Use agentic agent with read/write capabilities
            response_text = await agentic_agent.chat_async(
                request.message, request.session_id, request.kitchen_id
            )
            phase = "agentic_assistant"
            tools_used = True
        elif request.use_tools:
            # Use read-only tool agent
            response_text = await tool_agent.chat_async(
                request.message, request.session_id, request.kitchen_id
            )
            phase = "intelligent_assistant"
            tools_used = True
        else:
            # Use basic chatbot
            response_text = await basic_chatbot.chat_async(request.message, request.session_id)
            phase = "basic_chatbot"
            tools_used = False
        
        # Create structured response
        return ChatResponse(
            response=response_text,
            phase=phase,
            confidence=0.9 if len(response_text) > 10 else 0.7,
            tools_used=tools_used
        )
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        # Fallback to basic chatbot
        try:
            fallback_response = await basic_chatbot.chat_async(request.message, request.session_id)
            return ChatResponse(
                response=fallback_response,
                phase="fallback",
                confidence=0.6,
                tools_used=False
            )
        except:
            raise HTTPException(status_code=500, detail="Chat service unavailable")
