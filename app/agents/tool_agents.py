# app/agents/tool_agents.py
from typing import Dict, Any
from .base import BaseAgent, AgentResult
import requests
import json

class InventoryAgent(BaseAgent):
    def __init__(self, model_name: str = "qwen-2.5-7b-instruct", java_backend_url: str = "http://localhost:8080"):
        super().__init__("InventoryAgent", model_name)
        self.java_backend_url = java_backend_url
        
    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        operation = input_data.get("operation")
        
        try:
            if operation == "read":
                return self._get_inventory(input_data)
            elif operation == "create":
                return self._create_item(input_data)
            elif operation == "update":
                return self._update_item(input_data)
            elif operation == "delete":
                return self._delete_item(input_data)
            elif operation == "bulk_add":
                return self._bulk_add_items(input_data)
            else:
                return AgentResult(
                    success=False,
                    data={},
                    confidence=0.0,
                    error_message=f"Unknown operation: {operation}"
                )
        except Exception as e:
            return AgentResult(
                success=False,
                data={},
                confidence=0.0,
                error_message=str(e)
            )
    
    def _get_inventory(self, input_data: Dict[str, Any]) -> AgentResult:
        kitchen_id = input_data.get("kitchen_id", 1)
        response = requests.post(
            f"{self.java_backend_url}/api/internal/inventory/getAll",
            json={"kitchenId": kitchen_id}
        )
        
        if response.status_code == 200:
            return AgentResult(
                success=True,
                data={"inventory": response.json()},
                confidence=1.0,
                side_effects=["inventory_read"]
            )
        else:
            return AgentResult(
                success=False,
                data={},
                confidence=0.0,
                error_message="Failed to fetch inventory"
            )
    
    def _create_item(self, input_data: Dict[str, Any]) -> AgentResult:
        # Implementation for creating inventory item
        return AgentResult(
            success=True,
            data={"created": True},
            confidence=0.9,
            side_effects=["inventory_write", "stock_changed"]
        )
    
    def _update_item(self, input_data: Dict[str, Any]) -> AgentResult:
        # Implementation for updating inventory item
        return AgentResult(
            success=True,
            data={"updated": True},
            confidence=0.9,
            side_effects=["inventory_write", "stock_changed"]
        )
    
    def _delete_item(self, input_data: Dict[str, Any]) -> AgentResult:
        # Implementation for deleting inventory item
        return AgentResult(
            success=True,
            data={"deleted": True},
            confidence=0.9,
            side_effects=["inventory_write", "stock_changed"]
        )
    
    def _bulk_add_items(self, input_data: Dict[str, Any]) -> AgentResult:
        # Implementation for bulk adding items from OCR
        items = input_data.get("items", [])
        return AgentResult(
            success=True,
            data={"added_count": len(items)},
            confidence=0.85,
            side_effects=["inventory_write", "bulk_stock_changed"]
        )

class OCRAgent(BaseAgent):
    def __init__(self, model_name: str = "qwen-2.5-7b-instruct"):
        super().__init__("OCRAgent", model_name)
        
    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        # OCR processing implementation
        confidence = 0.92  # Mock confidence
        
        extracted_items = [
            {"name": "Milk", "quantity": 1, "unit": "gallon", "price": 3.99},
            {"name": "Bread", "quantity": 2, "unit": "loaf", "price": 2.49}
        ]
        
        return AgentResult(
            success=True,
            data={
                "extracted_items": extracted_items,
                "raw_text": "Mock OCR text"
            },
            confidence=confidence,
            side_effects=["ocr_processed"],
            metadata={"processing_time": 2.5}
        )

class RecipeAgent(BaseAgent):
    def __init__(self, model_name: str = "qwen-2.5-14b-instruct"):
        super().__init__("RecipeAgent", model_name)
        
    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        available_ingredients = input_data.get("available_ingredients", [])
        
        # Mock recipe generation
        recipes = [
            {
                "name": "Quick Pasta",
                "ingredients": ["pasta", "tomato sauce", "cheese"],
                "instructions": ["Boil pasta", "Add sauce", "Top with cheese"],
                "prep_time": 15
            }
        ]
        
        return AgentResult(
            success=True,
            data={"recipes": recipes},
            confidence=0.88,
            side_effects=[],
            metadata={"recipe_count": len(recipes)}
        )