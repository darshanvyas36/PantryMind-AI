# app/core/llm/parser.py
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from app.models.common import ExtractedItem, StorageType
from app.utils.exceptions import LLMError
import logging

logger = logging.getLogger(__name__)

class LLMResponseParser:
    
    def parse_bill_response(self, llm_response: str) -> List[ExtractedItem]:
        """Parse LLM response for bill extraction"""
        try:
            logger.info(f"Parsing bill response: {llm_response[:200]}...")
            json_data = self._extract_json(llm_response)
            logger.info(f"Extracted JSON data: {json_data}")
            
            items = []
            # Handle both 'items' and 'products' keys
            items_data = json_data.get('items', []) or json_data.get('products', [])
            
            for item_data in items_data:
                expiry_date = self._predict_expiry_date(item_data.get('raw_name', ''))
                quantity = item_data.get('quantity') or self._extract_quantity_from_name(item_data.get('raw_name', ''))
                unit = self._normalize_unit(item_data.get('unit'))
                
                item = ExtractedItem(
                    raw_name=item_data.get('raw_name', ''),
                    canonical_name=item_data.get('canonical_name'),
                    category=item_data.get('category'),
                    quantity=self._safe_float(quantity),
                    unit=unit,
                    price=self._safe_float(item_data.get('price')),
                    expiry_date=expiry_date,
                    expiry_source="estimated" if expiry_date else None,
                    is_food=item_data.get('is_food', True),
                    confidence=self._safe_float(item_data.get('confidence', 0.0))
                )
                items.append(item)
            
            logger.info(f"Parsed {len(items)} items from bill")
            return items
            
        except Exception as e:
            logger.error(f"Failed to parse bill response: {str(e)}")
            logger.error(f"Raw response was: {llm_response}")
            raise LLMError("PARSE_ERROR", f"Failed to parse LLM response: {str(e)}")

    def _extract_quantity_from_name(self, raw_name: str) -> Optional[float]:
        """Extract quantity from product name"""
        if not raw_name:
            return None
        
        # Look for patterns like "1kg", "5kg", "4-pack", "2L", etc.
        quantity_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:kg|g|l|ml|pack|pcs?|pieces?)',
            r'(\d+(?:\.\d+)?)\s*(?:liter|litre|gram|kilogram)',
            r'(\d+(?:\.\d+)?)-pack'
        ]
        
        for pattern in quantity_patterns:
            match = re.search(pattern, raw_name.lower())
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None


    def parse_label_response(self, llm_response: str) -> ExtractedItem:
        """Parse LLM response for label extraction"""
        try:
            logger.info(f"Parsing label response: {llm_response[:200]}...")
            json_data = self._extract_json(llm_response)
            logger.info(f"Extracted label JSON: {json_data}")
            
            if not json_data or not json_data.get('product_name'):
                logger.warning("No product information detected in label")
                return ExtractedItem(
                    raw_name="Unknown Product",
                    canonical_name="Unknown Product",
                    category="unknown",
                    quantity=None,
                    unit=None,
                    expiry_date=None,
                    expiry_source=None,
                    storage_type=StorageType.UNKNOWN,
                    brand=None,
                    is_food=True,
                    confidence=0.0
                )
            
            expiry_date = None
            expiry_source = None
            
            if json_data.get('expiry_date'):
                expiry_date = self._parse_date(json_data['expiry_date'])
                expiry_source = "explicit"
            else:
                expiry_date = self._predict_expiry_date(json_data.get('product_name', ''))
                expiry_source = "estimated" if expiry_date else None
            
            storage_type = StorageType.UNKNOWN
            if json_data.get('storage_type'):
                try:
                    storage_type = StorageType(json_data['storage_type'].lower())
                except ValueError:
                    storage_type = StorageType.UNKNOWN
            
            unit = self._normalize_unit(json_data.get('unit'))
            
            item = ExtractedItem(
                raw_name=json_data.get('product_name', ''),
                canonical_name=json_data.get('canonical_name'),
                category=json_data.get('category'),
                quantity=self._safe_float(json_data.get('quantity')),
                unit=unit,
                expiry_date=expiry_date,
                expiry_source=expiry_source,
                storage_type=storage_type,
                brand=json_data.get('brand'),
                is_food=json_data.get('is_food', True),
                confidence=self._safe_float(json_data.get('confidence', 0.0))
            )
            
            logger.info(f"Parsed label item: {item.raw_name}")
            return item
            
        except Exception as e:
            logger.error(f"Failed to parse label response: {str(e)}")
            logger.error(f"Raw response was: {llm_response}")
            raise LLMError("PARSE_ERROR", f"Failed to parse LLM response: {str(e)}")

    def parse_product_response(self, llm_response: str) -> List[ExtractedItem]:
        """Parse LLM response for product detection"""
        try:
            logger.info(f"Parsing product response: {llm_response[:200]}...")
            json_data = self._extract_json(llm_response)
            logger.info(f"Extracted product JSON: {json_data}")
            
            items = []
            products_data = json_data.get('products', []) or json_data.get('items', [])
            
            for product_data in products_data:
                quantity = self._safe_float(product_data.get('quantity'))
                unit = self._normalize_unit(product_data.get('unit'))
                product_name = product_data.get('product_name', '') or product_data.get('raw_name', '')
                expiry_date = self._predict_expiry_date(product_name)
                
                item = ExtractedItem(
                    raw_name=product_name,
                    canonical_name=product_data.get('canonical_name'),
                    category=product_data.get('category'),
                    brand=product_data.get('brand'),
                    quantity=quantity,
                    unit=unit,
                    expiry_date=expiry_date,
                    expiry_source="estimated" if expiry_date else None,
                    is_food=product_data.get('is_food', True),
                    confidence=self._safe_float(product_data.get('confidence', 0.0))
                )
                items.append(item)
            
            logger.info(f"Parsed {len(items)} items from product response")
            return items
            
        except Exception as e:
            logger.error(f"Failed to parse product response: {str(e)}")
            logger.error(f"Raw response was: {llm_response}")
            raise LLMError("PARSE_ERROR", f"Failed to parse LLM response: {str(e)}")

    def _extract_quantity_from_name(self, raw_name: str) -> Optional[float]:
        """Extract quantity from product name"""
        if not raw_name:
            return None
        
        # Look for patterns like "1kg", "5kg", "4-pack", "2L", etc.
        quantity_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:kg|g|l|ml|pack|pcs?|pieces?)',
            r'(\d+(?:\.\d+)?)\s*(?:liter|litre|gram|kilogram)',
            r'(\d+(?:\.\d+)?)-pack'
        ]
        
        for pattern in quantity_patterns:
            match = re.search(pattern, raw_name.lower())
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None

    def _normalize_unit(self, unit: str) -> Optional[str]:
        """Normalize unit to allowed values"""
        if not unit:
            return 'piece'
        
        unit = unit.lower().strip()
        
        if unit in ['kg', 'kilogram', 'kilograms']:
            return 'kg'
        elif unit in ['l', 'liter', 'liters', 'litre', 'litres']:
            return 'litre'
        elif unit in ['dozen']:
            return 'dozen'
        elif unit in ['g', 'gm', 'gram', 'grams', 'oz', 'pound', 'lb']:
            return 'grams'
        elif unit in ['ml', 'milliliter', 'milliliters', 'millilitre', 'millilitres', 'cup', 'tablespoon', 'teaspoon', 'fl oz']:
            return 'ml'
        elif unit in ['pcs', 'pc', 'pieces', 'piece', 'count', 'pack', 'bottle', 'can', 'box', 'bag']:
            return 'piece'
        
        logger.warning(f"Unknown unit '{unit}', defaulting to 'piece'")
        return 'piece'


    def _predict_expiry_date(self, product_name: str) -> Optional[date]:
        """Predict expiry date based on product type"""
        if not product_name:
            return None
        
        product_name = product_name.lower()
        today = date.today()
        
        if any(word in product_name for word in ['lettuce', 'spinach', 'herbs', 'berries']):
            return today + timedelta(days=3)
        elif any(word in product_name for word in ['banana', 'avocado', 'tomato']):
            return today + timedelta(days=5)
        elif any(word in product_name for word in ['apple', 'orange', 'carrot', 'potato']):
            return today + timedelta(days=14)
        elif any(word in product_name for word in ['milk', 'cream']):
            return today + timedelta(days=7)
        elif any(word in product_name for word in ['yogurt', 'cottage cheese']):
            return today + timedelta(days=14)
        elif 'cheese' in product_name:
            return today + timedelta(days=30)
        elif any(word in product_name for word in ['fish', 'seafood', 'chicken', 'beef', 'pork']):
            return today + timedelta(days=3)
        elif any(word in product_name for word in ['sausage', 'ham', 'bacon']):
            return today + timedelta(days=7)
        elif any(word in product_name for word in ['bread', 'bagel', 'muffin']):
            return today + timedelta(days=5)
        elif any(word in product_name for word in ['cereal', 'pasta', 'rice', 'flour']):
            return today + timedelta(days=365)
        elif any(word in product_name for word in ['canned', 'can', 'jar']):
            return today + timedelta(days=730)
        elif any(word in product_name for word in ['juice', 'soda', 'water']):
            return today + timedelta(days=180)
        else:
            return today + timedelta(days=30)

    def _extract_json(self, response: str) -> Dict[str, Any]:
        """Extract and fix JSON from LLM response, handling truncated responses"""
        try:
            logger.debug(f"Raw LLM response: '{response}'")
            
            if not response or not response.strip():
                logger.warning("Empty LLM response, returning empty products")
                return {"products": []}
            
            cleaned = response.strip()
            
            # Extract content from code blocks
            if '```json' in cleaned:
                match = re.search(r'```json\s*([\s\S]*?)(?:\s*```|$)', cleaned)
                if match:
                    cleaned = match.group(1)
            elif '```' in cleaned:
                match = re.search(r'```\s*([\s\S]*?)(?:\s*```|$)', cleaned)
                if match:
                    cleaned = match.group(1)
            
            # Try direct JSON parsing first
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    return {"items": parsed}
                return parsed
            except json.JSONDecodeError as e:
                logger.warning(f"Direct JSON parse failed: {e}")
            
            # Try to parse truncated JSON by extracting valid products
            return self._parse_truncated_json(cleaned)
            
        except Exception as e:
            logger.error(f"Failed to extract JSON: {str(e)}")
            logger.error(f"Response was: {response}")
            return self._parse_truncated_json(response)

    def _parse_truncated_json(self, json_str: str) -> Dict[str, Any]:
        """Parse truncated JSON by extracting valid item objects"""
        try:
            items = []
            
            # Look for complete item objects using regex (handle both raw_name and product_name)
            item_patterns = [
                r'\{\s*"raw_name"\s*:\s*"[^"]*"[^{}]*?\}',
                r'\{\s*"product_name"\s*:\s*"[^"]*"[^{}]*?\}'
            ]
            
            for pattern in item_patterns:
                matches = re.findall(pattern, json_str, re.DOTALL)
                
                for match in matches:
                    try:
                        clean_match = self._fix_json_issues(match)
                        item = json.loads(clean_match)
                        # Normalize field names
                        if 'product_name' in item and 'raw_name' not in item:
                            item['raw_name'] = item['product_name']
                        items.append(item)
                        logger.debug(f"Successfully parsed item: {item.get('raw_name', 'Unknown')}")
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse item object: {match[:100]}...")
                        continue
            
            if items:
                logger.info(f"Extracted {len(items)} items from truncated JSON")
                return {"items": items}
            
            # Alternative: extract item names and create minimal objects
            name_patterns = [
                r'"raw_name"\s*:\s*"([^"]*)"',
                r'"product_name"\s*:\s*"([^"]*)"'
            ]
            
            names = []
            for pattern in name_patterns:
                names.extend(re.findall(pattern, json_str))
            
            if names:
                logger.info(f"Found {len(names)} item names, creating minimal objects")
                for name in names:
                    items.append({
                        "raw_name": name,
                        "canonical_name": name,
                        "category": "unknown",
                        "brand": "Unknown",
                        "quantity": 1,
                        "unit": "piece",
                        "is_food": True,
                        "confidence": 0.5
                    })
                return {"items": items}
            
            logger.warning("Could not extract any valid items from truncated JSON")
            return {"items": []}
            
        except Exception as e:
            logger.error(f"Error in truncated JSON parsing: {str(e)}")
            return {"items": []}
    
    def _fix_json_issues(self, json_str: str) -> str:
        """Fix common JSON issues"""
        # Remove trailing commas
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        # Fix unquoted keys (but be careful not to break quoted strings)
        json_str = re.sub(r'(\w+):', r'"\1":', json_str)
        # Ensure proper closing
        if json_str.strip().startswith('{') and not json_str.strip().endswith('}'):
            json_str = json_str.rstrip() + '}'
        return json_str
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            try:
                return datetime.strptime(date_str, '%d/%m/%Y').date()
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")
                return None

# Global parser instance
llm_parser = LLMResponseParser()