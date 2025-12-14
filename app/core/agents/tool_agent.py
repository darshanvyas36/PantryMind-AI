# app/core/agents/tool_agent.py
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.tools import (
    InventoryLookupTool, RecipeSearchTool, KitchenAnalyticsTool,
    CategoryLookupTool, ShoppingListViewTool
)
from app.core.prompts.phase2_prompts import PHASE_2_SYSTEM_PROMPT, TOOL_ERROR_FALLBACK
from app.core.prompts.enhanced_system_prompt import ENHANCED_SYSTEM_PROMPT
from app.core.rag import RAGService
from app.core.memory import MemoryManager
from app.config.settings import settings
import logging
import json
import asyncio

logger = logging.getLogger(__name__)

class PantryMindToolAgent:
    """Modern LangChain tool agent with bind_tools"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openrouter_model,
            temperature=0.3,
            api_key=settings.openrouter_api_key or settings.gemini_api_key,
            base_url="https://openrouter.ai/api/v1",
            max_tokens=1500
        )
        
        # Initialize tool instances
        self.inventory_tool = InventoryLookupTool()
        self.recipe_tool = RecipeSearchTool()
        self.analytics_tool = KitchenAnalyticsTool()
        self.category_tool = CategoryLookupTool()
        self.shopping_tool = ShoppingListViewTool()
        
        # Initialize memory (RAG disabled for development)
        # self.rag_service = RAGService()  # Disabled to save API calls
        self.memory = MemoryManager()
        
        # Create tools and bind to LLM
        self.tools = self._create_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)
    
    def _create_tools(self):
        """Create modern LangChain tools"""
        
        @tool
        def get_inventory(kitchen_id: int) -> str:
            """Get current inventory items for a kitchen"""
            try:
                result = asyncio.run(self.inventory_tool.run(kitchen_id=kitchen_id))
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
            """Get kitchen analytics and consumption patterns"""
            try:
                result = asyncio.run(self.analytics_tool.run(kitchen_id=kitchen_id))
                return json.dumps(result)
            except Exception as e:
                return f"Error: {str(e)}"
        
        @tool
        def get_categories() -> str:
            """Get available food categories and units"""
            try:
                result = asyncio.run(self.category_tool.run())
                return json.dumps(result)
            except Exception as e:
                return f"Error: {str(e)}"
        
        @tool
        def get_shopping_lists(kitchen_id: int) -> str:
            """Get shopping lists for a kitchen"""
            try:
                result = asyncio.run(self.shopping_tool.run(kitchen_id=kitchen_id))
                return json.dumps(result)
            except Exception as e:
                return f"Error: {str(e)}"
        
        return [get_inventory, search_recipes, get_analytics, get_categories, get_shopping_lists]
    
    async def chat_async(self, user_input: str, session_id: str = "default", 
                        kitchen_id: int = 1, user_id: str = None) -> str:
        """Process user input with modern tool calling"""
        try:
            # Get user context from memory
            user_id = user_id or f"kitchen_{kitchen_id}"
            context = self.memory.get_recent_context(user_id, limit=2)
            
            user_lower = user_input.lower()
            
            # Recipe queries
            if any(word in user_lower for word in ['cook', 'recipe', 'meal', 'dinner']):
                logger.info(f"Recipe query detected for kitchen {kitchen_id}")
                result = await self.recipe_tool.run(kitchen_id=kitchen_id)
                recipes = result.get('recipe_suggestions', [])
                if recipes:
                    recipe_text = ', '.join([f"{r['name']} ({r['availability_score']}% available)" for r in recipes[:3]])
                    
                    # RAG disabled for development
                    # recipe_names = [r['name'] for r in recipes[:2]]
                    # rag_advice = self.rag_service.get_contextual_advice(recipe_names, "cooking")
                    
                    return f"Here are recipes you can make: {recipe_text}"
                else:
                    return "I couldn't find recipes with your current ingredients."
            
            # Analytics queries
            elif any(word in user_lower for word in ['waste', 'wasting', 'analytics']):
                logger.info(f"Analytics query detected for kitchen {kitchen_id}")
                result = await self.analytics_tool.run(kitchen_id=kitchen_id)
                insights = result.get('insights', [])
                if insights:
                    return f"Kitchen insights: {'. '.join(insights)}"
                else:
                    return "Your kitchen analytics are being processed."
            
            # Shopping queries
            elif any(word in user_lower for word in ['buy', 'shopping', 'shop']):
                logger.info(f"Shopping query detected for kitchen {kitchen_id}")
                result = await self.shopping_tool.run(kitchen_id=kitchen_id)
                stats = result.get('statistics', {})
                return f"Shopping: {stats.get('total_active_lists', 0)} active lists, {stats.get('pending_items', 0)} pending items"
            
            # Inventory queries
            elif any(word in user_lower for word in ['inventory', 'items', 'expiring', 'pantry']):
                logger.info(f"Inventory query detected for kitchen {kitchen_id}")
                result = await self.inventory_tool.run(kitchen_id=kitchen_id)
                
                if 'expiring' in user_lower:
                    expired_items = result.get('expired_items', [])
                    if expired_items:
                        items_list = [item.get('description', f"Item-{item.get('id', 'Unknown')}") for item in expired_items[:5]]
                        items_text = ', '.join(items_list)
                        
                        # RAG disabled for development
                        # rag_advice = self.rag_service.get_contextual_advice(items_list, "expiring food")
                        
                        return f"Items expiring soon: {items_text}. Total expired items: {len(expired_items)}"
                    else:
                        return "Great news! No items are expiring soon."
                else:
                    total_items = result.get('total_items', 0)
                    expired_count = result.get('expired_count', 0)
                    
                    # RAG disabled for development
                    # rag_advice = self.rag_service.enhance_response("inventory management tips")
                    
                    return f"You have {total_items} items in your inventory. {expired_count} items are expired or expiring soon."
            
            # Fallback to LLM
            messages = [
                SystemMessage(content=f"{ENHANCED_SYSTEM_PROMPT}\n\nKitchen ID: {kitchen_id}"),
                HumanMessage(content=user_input)
            ]
            
            response = await self.llm_with_tools.ainvoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"Tool agent error: {str(e)}")
            return TOOL_ERROR_FALLBACK