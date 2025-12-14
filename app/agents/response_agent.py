# app/agents/response_agent.py
from typing import Dict, Any
from .base import BaseAgent, AgentResult

class ResponseAgent(BaseAgent):
    def __init__(self, model_name: str = "qwen-2.5-14b-instruct"):
        super().__init__("ResponseAgent", model_name)
        
    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        execution_state = input_data.get("execution_state")
        context = input_data.get("context", {})
        
        if execution_state == "error":
            return self._generate_error_response(context)
        elif execution_state == "success":
            return self._generate_success_response(context)
        else:
            return self._generate_help_response(context)
    
    def _generate_error_response(self, context: Dict[str, Any]) -> AgentResult:
        error_reason = context.get("error_reason", "Unknown error")
        
        error_responses = {
            "Low intent confidence": "I'm not sure what you're asking for. Could you please be more specific? For example, you can ask me to 'check inventory', 'add new item', or 'find recipes'.",
            "OCR confidence too low": "I had trouble reading your receipt clearly. Could you try uploading a clearer image or manually enter the items?",
            "Validation failed": "There was an issue with the data provided. Please check your input and try again.",
            "Exceeds max plan steps": "Your request is too complex. Please break it down into smaller, specific tasks."
        }
        
        response = error_responses.get(error_reason, f"Sorry, there was an error: {error_reason}")
        
        return AgentResult(
            success=True,
            data={"response": response},
            confidence=1.0,
            metadata={"response_type": "error"}
        )
    
    def _generate_success_response(self, context: Dict[str, Any]) -> AgentResult:
        intent = context.get("intent")
        execution_results = context.get("execution_results", [])
        plan_steps = context.get("plan_steps", [])
        
        # Check plan steps for direct response types
        if plan_steps:
            first_step = plan_steps[0]
            tool_type = first_step.get("tool_type")
            if tool_type == "greeting":
                return self._format_greeting_response(execution_results)
            elif tool_type == "help":
                return self._format_help_response(execution_results)
        
        if intent == "inventory":
            return self._format_inventory_response(execution_results)
        elif intent == "recipe":
            return self._format_recipe_response(execution_results)
        elif intent == "ocr":
            return self._format_ocr_response(execution_results)
        elif intent == "analytics":
            return self._format_analytics_response(execution_results)
        elif intent == "greeting":
            return self._format_greeting_response(execution_results)
        elif intent == "help":
            return self._format_help_response(execution_results)
        else:
            return self._format_generic_response(execution_results)
    
    def _format_inventory_response(self, results: list) -> AgentResult:
        if not results:
            response = "No inventory data available."
        else:
            result = results[0]
            if result.get("operation") == "read":
                inventory = result.get("data", {}).get("inventory", [])
                response = f"Found {len(inventory)} items in your pantry. Here's what you have:\n"
                for item in inventory[:5]:  # Show first 5 items
                    response += f"• {item.get('name', 'Unknown')} - {item.get('quantity', 0)} {item.get('unit', '')}\n"
                if len(inventory) > 5:
                    response += f"... and {len(inventory) - 5} more items."
            else:
                response = "Inventory updated successfully!"
        
        return AgentResult(
            success=True,
            data={"response": response},
            confidence=0.9,
            metadata={"response_type": "inventory"}
        )
    
    def _format_recipe_response(self, results: list) -> AgentResult:
        recipes = []
        for result in results:
            if result.get("data", {}).get("recipes"):
                recipes.extend(result["data"]["recipes"])
        
        if not recipes:
            response = "No recipes found with your available ingredients."
        else:
            response = f"I found {len(recipes)} recipe(s) you can make:\n\n"
            for recipe in recipes[:3]:  # Show first 3 recipes
                response += f"🍽️ **{recipe.get('name', 'Unknown Recipe')}**\n"
                response += f"⏱️ Prep time: {recipe.get('prep_time', 'Unknown')} minutes\n"
                ingredients = recipe.get('ingredients', [])
                response += f"📝 Ingredients: {', '.join(ingredients[:5])}\n\n"
        
        return AgentResult(
            success=True,
            data={"response": response},
            confidence=0.9,
            metadata={"response_type": "recipe"}
        )
    
    def _format_ocr_response(self, results: list) -> AgentResult:
        extracted_items = []
        for result in results:
            if result.get("data", {}).get("extracted_items"):
                extracted_items.extend(result["data"]["extracted_items"])
        
        if not extracted_items:
            response = "No items could be extracted from the receipt."
        else:
            response = f"Successfully extracted {len(extracted_items)} items from your receipt:\n\n"
            for item in extracted_items:
                response += f"• {item.get('name', 'Unknown')} - {item.get('quantity', 0)} {item.get('unit', '')} (${item.get('price', 0):.2f})\n"
            response += "\nThese items have been added to your inventory!"
        
        return AgentResult(
            success=True,
            data={"response": response},
            confidence=0.9,
            metadata={"response_type": "ocr"}
        )
    
    def _format_analytics_response(self, results: list) -> AgentResult:
        response = "Here's your pantry analytics summary:\n\n"
        response += "📊 Total items: 45\n"
        response += "⚠️ Items expiring soon: 3\n"
        response += "💰 Total value: $127.50\n"
        response += "📈 Most used category: Dairy\n"
        
        return AgentResult(
            success=True,
            data={"response": response},
            confidence=0.9,
            metadata={"response_type": "analytics"}
        )
    
    def _format_greeting_response(self, results: list) -> AgentResult:
        response = "Hello! 👋 I'm your PantryMind assistant. I can help you manage your inventory, find recipes, process receipts, and analyze your pantry data. What would you like to do today?"
        
        return AgentResult(
            success=True,
            data={"response": response},
            confidence=1.0,
            metadata={"response_type": "greeting"}
        )
    
    def _format_help_response(self, results: list) -> AgentResult:
        response = """🤖 **PantryMind Assistant Help**

I can help you with:

📦 **Inventory Management**
• "Check my inventory" - View all items
• "Add milk to inventory" - Add new items
• "Update bread quantity to 2" - Modify existing items

🍳 **Recipe Suggestions**
• "What can I cook?" - Get recipes based on your ingredients
• "Find pasta recipes" - Search for specific recipes

📄 **Receipt Processing**
• "Process my receipt" - Upload and extract items from receipts

📊 **Analytics**
• "Show my pantry stats" - Get inventory analytics and reports

Just ask me naturally, and I'll help you manage your pantry efficiently!"""
        
        return AgentResult(
            success=True,
            data={"response": response},
            confidence=1.0,
            metadata={"response_type": "help"}
        )
    
    def _format_generic_response(self, results: list) -> AgentResult:
        response = "I've completed your request. Is there anything else I can help you with?"
        
        return AgentResult(
            success=True,
            data={"response": response},
            confidence=0.8,
            metadata={"response_type": "generic"}
        )
    
    def _generate_help_response(self, context: Dict[str, Any]) -> AgentResult:
        return self._format_help_response([])