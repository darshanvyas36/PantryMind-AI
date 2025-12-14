# app/agents/validator_agent.py
from typing import Dict, Any
from .base import BaseAgent, AgentResult

class ValidatorAgent(BaseAgent):
    def __init__(self, model_name: str = "qwen-2.5-7b-instruct"):
        super().__init__("ValidatorAgent", model_name)
        
    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        validation_type = input_data.get("validation_type")
        data_to_validate = input_data.get("data")
        
        if validation_type == "ocr_result":
            return self._validate_ocr_result(data_to_validate)
        elif validation_type == "inventory_write":
            return self._validate_inventory_write(data_to_validate)
        elif validation_type == "schema":
            return self._validate_schema(data_to_validate, input_data.get("schema"))
        else:
            return AgentResult(
                success=False,
                data={"is_valid": False},
                confidence=1.0,
                error_message="Unknown validation type"
            )
    
    def _validate_ocr_result(self, ocr_data: Dict[str, Any]) -> AgentResult:
        confidence = ocr_data.get("confidence", 0.0)
        extracted_items = ocr_data.get("extracted_items", [])
        
        # Validation rules for OCR
        is_valid = True
        errors = []
        
        if confidence < 0.8:
            is_valid = False
            errors.append("OCR confidence too low")
        
        if not extracted_items:
            is_valid = False
            errors.append("No items extracted")
        
        # Validate each item
        for item in extracted_items:
            if not item.get("name"):
                is_valid = False
                errors.append("Item missing name")
            
            quantity = item.get("quantity", 0)
            if quantity <= 0:
                is_valid = False
                errors.append(f"Invalid quantity for {item.get('name', 'unknown item')}")
        
        return AgentResult(
            success=True,
            data={
                "is_valid": is_valid,
                "errors": errors,
                "validated_items": len(extracted_items)
            },
            confidence=1.0,
            metadata={"validation_type": "ocr_result"}
        )
    
    def _validate_inventory_write(self, inventory_data: Dict[str, Any]) -> AgentResult:
        is_valid = True
        errors = []
        
        # Required fields validation
        required_fields = ["name", "quantity", "unit"]
        for field in required_fields:
            if not inventory_data.get(field):
                is_valid = False
                errors.append(f"Missing required field: {field}")
        
        # Business logic validation
        quantity = inventory_data.get("quantity", 0)
        if quantity < 0:
            is_valid = False
            errors.append("Quantity cannot be negative")
        
        # Check for duplicate items (mock check)
        name = inventory_data.get("name", "").lower()
        if name in ["existing_item"]:  # Mock existing items
            is_valid = False
            errors.append("Item already exists")
        
        return AgentResult(
            success=True,
            data={
                "is_valid": is_valid,
                "errors": errors
            },
            confidence=1.0,
            metadata={"validation_type": "inventory_write"}
        )
    
    def _validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> AgentResult:
        # Basic schema validation
        is_valid = True
        errors = []
        
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in data:
                is_valid = False
                errors.append(f"Missing required field: {field}")
        
        return AgentResult(
            success=True,
            data={
                "is_valid": is_valid,
                "errors": errors
            },
            confidence=1.0,
            metadata={"validation_type": "schema"}
        )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "input_schema": {
                "validation_type": {"type": "string", "required": True},
                "data": {"type": "object", "required": True}
            },
            "output_schema": {
                "is_valid": {"type": "boolean"},
                "errors": {"type": "array", "items": {"type": "string"}}
            },
            "preconditions": ["validation_type must be supported"],
            "side_effects": []
        }