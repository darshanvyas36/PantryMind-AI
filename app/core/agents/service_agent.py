# app/core/agents/service_agent.py
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.tools.service_tool import ServiceTool
from app.config.settings import settings
import logging
import json
import asyncio

logger = logging.getLogger(__name__)

SERVICE_SYSTEM_PROMPT = """
You are PantryMind, an autonomous kitchen assistant with direct access to service methods.

🛠️ AVAILABLE OPERATIONS via service_tool:
- get_inventory: View all inventory items
- get_low_stock: Find items running low
- get_expired: Find expired/expiring items  
- add_to_shopping_list: Add item to shopping list (name, quantity)

🎯 BEHAVIOR:
1. ALWAYS use service_tool for kitchen operations
2. Map user requests to correct operations
3. Provide clear responses with actual data

🔄 EXAMPLES:
User: "What items are low on stock?"
→ Use: service_tool(operation="get_low_stock", kitchen_id=1)

User: "Add milk to shopping list"  
→ Use: service_tool(operation="add_to_shopping_list", kitchen_id=1, name="milk", quantity=1)

ALWAYS use the service_tool for any kitchen-related request!
"""

class ServiceAgent:
    """Agent using direct service calls"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openrouter_model,
            temperature=0.3,
            api_key=settings.openrouter_api_key or settings.gemini_api_key,
            base_url="https://openrouter.ai/api/v1",
            max_tokens=1500
        )
        
        self.service_tool_instance = ServiceTool()
        self.tools = self._create_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)
    
    def _create_tools(self):
        """Create service tool for LangChain"""
        
        @tool
        def service_tool(operation: str, kitchen_id: int, **kwargs) -> str:
            """
            Direct service tool for PantryMind operations.
            
            Args:
                operation: get_inventory, get_low_stock, get_expired, add_to_shopping_list
                kitchen_id: Kitchen ID (usually 1)
                **kwargs: Additional parameters (name, quantity for add operations)
            """
            try:
                result = asyncio.run(self.service_tool_instance.run(
                    operation=operation, 
                    kitchen_id=kitchen_id, 
                    **kwargs
                ))
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Service tool error: {str(e)}")
                return json.dumps({"error": str(e)})
        
        return [service_tool]
    
    async def chat_async(self, user_input: str, session_id: str = "default", 
                        kitchen_id: int = 1, user_id: str = None) -> str:
        """Process user input with service calls"""
        try:
            messages = [
                SystemMessage(content=f"{SERVICE_SYSTEM_PROMPT}\n\nKitchen ID: {kitchen_id}"),
                HumanMessage(content=user_input)
            ]
            
            response = await self.llm_with_tools.ainvoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"Service agent error: {str(e)}")
            return "I'm having trouble processing your request. Please try again."