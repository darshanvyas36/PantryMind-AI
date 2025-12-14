# app/core/agents/fully_agentic_agent.py
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.tools.comprehensive_tool import ComprehensivePantryTool
from app.core.memory import MemoryManager
from app.config.settings import settings
import logging
import json
import asyncio

logger = logging.getLogger(__name__)

FULLY_AGENTIC_SYSTEM_PROMPT = """
You are PantryMind, a FULLY AUTONOMOUS kitchen assistant that can perform ANY task a user can do manually.

🎯 CORE CAPABILITIES:
You have COMPLETE access to all PantryMind operations through the comprehensive_pantry_tool.

🛠️ AVAILABLE OPERATIONS:
- get_inventory: View all inventory items
- get_low_stock: Find items running low
- get_expired: Find expired/expiring items  
- add_inventory: Add new items (name, quantity, categoryId, unitId, expiryDate, price)
- update_inventory: Update existing items (item_id + fields to update)
- delete_inventory: Remove items (item_id)
- consume_items: Mark items as consumed (items list)
- get_shopping_lists: View shopping lists
- add_to_shopping_list: Add items to shopping list (name, quantity, unitId, categoryId)
- mark_purchased: Mark shopping items as bought (item_id)
- get_analytics: Kitchen insights and patterns
- get_categories: Available food categories
- get_units: Available measurement units
- search_recipes: Find recipes based on ingredients
- get_notifications: View alerts and notifications

🎯 AGENTIC BEHAVIOR:
1. ALWAYS use the comprehensive_pantry_tool for ANY kitchen-related request
2. UNDERSTAND user intent and map to correct operations
3. ASK for missing information if needed (like quantities, categories)
4. EXECUTE operations step by step
5. PROVIDE clear feedback on what was done
6. SUGGEST related actions when helpful

🔄 EXAMPLE INTERACTIONS:
User: "What items are low on stock?"
→ Use: comprehensive_pantry_tool(operation="get_low_stock", kitchen_id=1)

User: "Add milk to my shopping list"  
→ Use: comprehensive_pantry_tool(operation="add_to_shopping_list", kitchen_id=1, name="milk", quantity=1)

User: "What's expiring soon?"
→ Use: comprehensive_pantry_tool(operation="get_expired", kitchen_id=1)

User: "Add 2 liters of milk to inventory"
→ Use: comprehensive_pantry_tool(operation="add_inventory", kitchen_id=1, name="milk", quantity=2, unitId=2)

REMEMBER: You can perform ANY task - reading data, adding items, updating quantities, managing shopping lists, etc.
ALWAYS use the tool for kitchen operations. Be proactive and helpful!
"""

class FullyAgenticAgent:
    """Fully autonomous agent with complete PantryMind access"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openrouter_model,
            temperature=0.3,
            api_key=settings.openrouter_api_key or settings.gemini_api_key,
            base_url="https://openrouter.ai/api/v1",
            max_tokens=2000
        )
        
        # Initialize comprehensive tool
        self.comprehensive_tool = ComprehensivePantryTool()
        self.memory = MemoryManager()
        
        # Create tools and bind to LLM
        self.tools = self._create_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)
    
    def _create_tools(self):
        """Create comprehensive tool for LangChain"""
        
        @tool
        def comprehensive_pantry_tool(operation: str, kitchen_id: int, **kwargs) -> str:
            """
            Complete PantryMind operations tool. Can perform ANY task a user can do manually.
            
            Args:
                operation: The operation to perform (get_inventory, add_inventory, get_low_stock, etc.)
                kitchen_id: Kitchen ID (usually 1)
                **kwargs: Additional parameters based on operation
                
            Operations:
            - get_inventory: View all inventory items
            - get_low_stock: Find items running low  
            - get_expired: Find expired/expiring items
            - add_inventory: Add new items (name, quantity, categoryId, unitId, expiryDate, price)
            - update_inventory: Update items (item_id + fields)
            - delete_inventory: Remove items (item_id)
            - consume_items: Mark consumed (items list)
            - get_shopping_lists: View shopping lists
            - add_to_shopping_list: Add to shopping list (name, quantity, unitId, categoryId)
            - mark_purchased: Mark as bought (item_id)
            - get_analytics: Kitchen insights
            - get_categories: Available categories
            - get_units: Available units
            - search_recipes: Find recipes
            - get_notifications: View alerts
            """
            try:
                result = asyncio.run(self.comprehensive_tool.run(
                    operation=operation, 
                    kitchen_id=kitchen_id, 
                    **kwargs
                ))
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Tool error: {str(e)}")
                return json.dumps({"error": str(e)})
        
        return [comprehensive_pantry_tool]
    
    async def chat_async(self, user_input: str, session_id: str = "default", 
                        kitchen_id: int = 1, user_id: str = None) -> str:
        """Process user input with full agentic capabilities"""
        try:
            # Get conversation context
            user_id = user_id or f"kitchen_{kitchen_id}"
            context = self.memory.get_recent_context(user_id, limit=3)
            
            # Build messages with context
            messages = [
                SystemMessage(content=f"{FULLY_AGENTIC_SYSTEM_PROMPT}\n\nKitchen ID: {kitchen_id}"),
            ]
            
            # Add conversation context if available
            if context:
                messages.append(SystemMessage(content=f"Recent conversation context:\n{context}"))
            
            messages.append(HumanMessage(content=user_input))
            
            # Get response with tool calling
            response = await self.llm_with_tools.ainvoke(messages)
            
            # Store interaction in memory
            self.memory.add_interaction(user_id, user_input, response.content)
            
            return response.content
            
        except Exception as e:
            logger.error(f"Fully agentic agent error: {str(e)}")
            return "I'm having trouble processing your request. Please try again or be more specific about what you'd like me to do."