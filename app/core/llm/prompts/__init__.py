# app/core/llm/prompts/__init__.py
from .bill_prompts import BillPrompts
from .label_prompts import LabelPrompts
from .product_prompts import ProductPrompts
from .advanced_prompts import AdvancedRecipePrompts
from .category_recipe_prompts import CategoryRecipePrompts
from .search_recipe_prompts import SearchRecipePrompts

# Backward compatibility
class PromptTemplates:
    @staticmethod
    def bill_vision_prompt(locale: str = "en-IN") -> str:
        return BillPrompts.vision_extraction(locale)
    
    @staticmethod
    def bill_extraction_prompt(ocr_text: str, locale: str = "en-IN") -> str:
        return BillPrompts.ocr_fallback(ocr_text, locale)
    
    @staticmethod
    def label_vision_prompt() -> str:
        return LabelPrompts.vision_extraction()
    
    @staticmethod
    def label_extraction_prompt(ocr_text: str) -> str:
        return LabelPrompts.ocr_fallback(ocr_text)
    
    @staticmethod
    def product_detection_prompt(mode: str = "auto") -> str:
        if mode == "single":
            return ProductPrompts.single_detection()
        else:
            return ProductPrompts.multi_detection()
