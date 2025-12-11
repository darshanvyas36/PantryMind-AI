# app/core/llm/prompts/product_prompts.py
# class ProductPrompts:
    
#     @staticmethod
#     def single_detection() -> str:
#         return """Identify the main food/grocery product in this image. Return ONLY valid JSON:

# {"products":[{"product_name":"Coca Cola 330ml","canonical_name":"Cola","category":"beverages","brand":"Coca Cola","quantity":330,"unit":"ml","expiry_date":null,"storage_type":"pantry","is_food":true,"confidence":0.9}]}

# Look for ANY food/drink items. Include brand names, sizes, specific details."""

#     @staticmethod
#     def multi_detection() -> str:
#         return """Identify ALL visible food items in this fridge/shelf image. Return ONLY valid JSON:

# {"products":[{"product_name":"Milk 1L","canonical_name":"Milk","category":"dairy","brand":"Amul","quantity":1000,"unit":"ml","expiry_date":null,"storage_type":"fridge","is_food":true,"confidence":0.8},{"product_name":"Bread Loaf","canonical_name":"Bread","category":"bakery","brand":"Unknown","quantity":1,"unit":"piece","expiry_date":null,"storage_type":"pantry","is_food":true,"confidence":0.7}]}

# Scan systematically. Look for bottles, containers, packages, fresh produce."""


# app/core/llm/prompts/product_prompts.py
class ProductPrompts:
    
    @staticmethod
    def single_detection(categories: list = None, units: list = None, locations: list = None) -> str:
        category_list = ", ".join([cat.get("name", "") for cat in (categories or [])])
        unit_list = ", ".join([unit.get("name", "") for unit in (units or [])])
        location_list = ", ".join([loc.get("name", "") for loc in (locations or [])])
        
        return f"""Identify the main food/grocery product in this image. Return ONLY valid JSON:

{{"products":[{{"product_name":"Coca Cola 330ml","canonical_name":"Cola","category":"beverages","brand":"Coca Cola","quantity":330,"unit":"ml","expiry_date":null,"storage_type":"pantry","is_food":true,"confidence":0.9}}]}}

Use ONLY these categories: {category_list or "beverages, dairy, staples"}
Use ONLY these units: {unit_list or "ml, litre, grams, kg, piece"}
Use ONLY these locations: {location_list or "pantry, fridge, freezer"}
Look for ANY food/drink items. Include brand names, sizes, specific details."""

    @staticmethod
    def multi_detection(categories: list = None, units: list = None, locations: list = None) -> str:
        category_list = ", ".join([cat.get("name", "") for cat in (categories or [])])
        unit_list = ", ".join([unit.get("name", "") for unit in (units or [])])
        location_list = ", ".join([loc.get("name", "") for loc in (locations or [])])
        
        return f"""Identify ALL visible food items in this fridge/shelf image. Return ONLY valid JSON:

{{"products":[{{"product_name":"Milk 1L","canonical_name":"Milk","category":"dairy","brand":"Amul","quantity":1000,"unit":"ml","expiry_date":null,"storage_type":"fridge","is_food":true,"confidence":0.8}},{{"product_name":"Bread Loaf","canonical_name":"Bread","category":"bakery","brand":"Unknown","quantity":1,"unit":"piece","expiry_date":null,"storage_type":"pantry","is_food":true,"confidence":0.7}}]}}

Use ONLY these categories: {category_list or "beverages, dairy, staples"}
Use ONLY these units: {unit_list or "ml, litre, grams, kg, piece"}
Use ONLY these locations: {location_list or "pantry, fridge, freezer"}
Scan systematically. Look for bottles, containers, packages, fresh produce."""
