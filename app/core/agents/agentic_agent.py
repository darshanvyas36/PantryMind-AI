# app/core/agents/agentic_agent.py
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.core.tools import (
    InventoryLookupTool, RecipeSearchTool, KitchenAnalyticsTool,
    CategoryLookupTool, ShoppingListViewTool
)
from app.core.tools.inventory_write_tool import InventoryWriteTool
from app.core.tools.shopping_write_tool import ShoppingWriteTool
from app.core.memory import MemoryManager
from app.config.settings import settings
import logging
import json
import asyncio

logger = logging.getLogger(__name__)

AGENTIC_SYSTEM_PROMPT = """
You are PantryMind, a fully autonomous kitchen assistant that can perform ALL tasks on behalf of users.

🎯 CORE CAPABILITIES:
You can READ and WRITE data, manage inventory, create shopping lists, and handle complex multi-step tasks.

🛠️ AVAILABLE TOOLS:
READ TOOLS:
- get_inventory(kitchen_id) - View current inventory
- search_recipes(kitchen_id) - Find recipes  
- get_analytics(kitchen_id) - Kitchen insights
- get_categories() - Categories and units
- get_shopping_lists(kitchen_id) - View shopping lists

WRITE TOOLS:
- manage_inventory(kitchen_id, operation, item_data) - Add/update/delete/consume items
- manage_shopping(kitchen_id, operation, data) - Create lists, add items, mark purchased

🎯 AGENTIC BEHAVIOR:
1. UNDERSTAND user intent completely
2. ASK for missing information if needed
3. CONFIRM actions before executing
4. EXECUTE tasks step by step
5. PROVIDE clear feedback on results

🔄 CONVERSATION PATTERNS:
- "Add milk to inventory" → Ask quantity, expiry → Execute → Confirm
- "Create shopping list" → Ask name, type → Create → Add items if mentioned
- "I bought groceries" → Ask what items → Add to inventory → Update shopping list
- "Plan dinner" → Check inventory → Suggest recipes → Ask preferences → Provide recipe

🎯 INTERACTION GUIDELINES:
- Be proactive and helpful
- Ask clarifying questions when needed
- Confirm destructive actions (delete, consume)
- Provide step-by-step guidance for complex tasks
- Remember context within conversation
- Suggest related actions ("Would you like me to add this to your shopping list?")

REMEMBER: You can perform ANY kitchen management task - just ask for details and execute!
"""

class AgenticAgent:
    """Fully autonomous agent that can perform all kitchen tasks"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openrouter_model,
            temperature=0.3,
            api_key=settings.openrouter_api_key or settings.gemini_api_key,
            base_url="https://openrouter.ai/api/v1",
            max_tokens=2000
        )
        
        # Initialize all tools
        self.inventory_read = InventoryLookupTool()
        self.recipe_tool = RecipeSearchTool()
        self.analytics_tool = KitchenAnalyticsTool()
        self.category_tool = CategoryLookupTool()
        self.shopping_read = ShoppingListViewTool()
        
        # Write tools
        self.inventory_write = InventoryWriteTool()
        self.shopping_write = ShoppingWriteTool()
        
        # Memory and tools
        self.memory = MemoryManager()
        self.tools = self._create_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)
    
    def _create_tools(self):
        """Create all agentic tools"""
        
        @tool
        def get_inventory(kitchen_id: int) -> str:
            """Get current inventory items"""
            try:
                result = asyncio.run(self.inventory_read.run(kitchen_id=kitchen_id))
                return json.dumps(result)
            except Exception as e:
                return f"Error: {str(e)}"
        
        @tool
        def manage_inventory(kitchen_id: int, operation: str, item_data: str) -> str:
            """Add, update, delete, or consume inventory items. Operations: add, update, delete, consume"""
            try:
                data = json.loads(item_data) if isinstance(item_data, str) else item_data
                result = asyncio.run(self.inventory_write.run(kitchen_id=kitchen_id, operation=operation, item_data=data))
                return json.dumps(result)
            except Exception as e:
                return f"Error: {str(e)}"
        
        @tool
        def search_recipes(kitchen_id: int) -> str:
            """Find recipes based on available ingredients"""
            try:
                result = asyncio.run(self.recipe_tool.run(kitchen_id=kitchen_id))
                return json.dumps(result)
            except Exception as e:
                return f"Error: {str(e)}"
        
        @tool
        def get_analytics(kitchen_id: int) -> str:
            """Get kitchen analytics and insights"""
            try:
                result = asyncio.run(self.analytics_tool.run(kitchen_id=kitchen_id))
                return json.dumps(result)
            except Exception as e:
                return f"Error: {str(e)}"
        
        @tool
        def get_categories() -> str:
            """Get available categories and units"""
            try:
                result = asyncio.run(self.category_tool.run())
                return json.dumps(result)
            except Exception as e:
                return f"Error: {str(e)}"
        
        @tool
        def manage_shopping(kitchen_id: int, operation: str, data: str) -> str:
            """Manage shopping lists. Operations: create_list, add_item, mark_purchased, delete_item"""
            try:
                parsed_data = json.loads(data) if isinstance(data, str) else data
                result = asyncio.run(self.shopping_write.run(kitchen_id=kitchen_id, operation=operation, data=parsed_data))
                return json.dumps(result)
            except Exception as e:
                return f"Error: {str(e)}"
        
        @tool
        def get_shopping_lists(kitchen_id: int) -> str:
            """View current shopping lists"""
            try:
                result = asyncio.run(self.shopping_read.run(kitchen_id=kitchen_id))
                return json.dumps(result)
            except Exception as e:
                return f"Error: {str(e)}"
        
        return [get_inventory, manage_inventory, search_recipes, get_analytics, 
                get_categories, manage_shopping, get_shopping_lists]
    
    async def chat_async(self, user_input: str, session_id: str = "default", 
                        kitchen_id: int = 1, user_id: str = None) -> str:
        """Process user input with full agentic capabilities"""
        try:
            # Get conversation context
            user_id = user_id or f"kitchen_{kitchen_id}"
            context = self.memory.get_recent_context(user_id, limit=3)
            
            # Build messages with context
            messages = [
                SystemMessage(content=f"{AGENTIC_SYSTEM_PROMPT}\n\nKitchen ID: {kitchen_id}"),
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
            logger.error(f"Agentic agent error: {str(e)}")
            return "I'm having trouble processing your request. Please try again or be more specific about what you'd like me to do."