from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
import unicodedata
import httpx

router = APIRouter()

def normalize_name(name: str) -> str:
    if not name or not name.strip():
        return ""
    
    normalized = name.lower().strip()
    normalized = unicodedata.normalize('NFD', normalized)
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    normalized = re.sub(r'[^a-z\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    if normalized.endswith('s') and len(normalized) > 1:
        normalized = normalized[:-1]
    
    return normalized

# def categorize_by_inventory_data(item_name: str, inventory_items: List[Dict]) -> str:
#     """Categorize based on actual inventory category and expiry patterns"""
    
#     # Find matching inventory item
#     matching_item = None
#     for inv_item in inventory_items:
#         if inv_item.get('itemName') == item_name:
#             matching_item = inv_item
#             break
    
#     if not matching_item:
#         print(f"No inventory match found for: {item_name}")
#         return 'MONTHLY'  # Safe default
    
#     try:
#         # Method 1: Use inventory category if available
#         category_info = matching_item.get('category', {})
#         category_name = category_info.get('name', '').lower() if category_info else ''
        
#         print(f"Item: {item_name}, Category: {category_name}")
        
#         if category_name:
#             # Map inventory categories to shopping frequencies
#             if any(cat in category_name for cat in ['dairy', 'fresh', 'produce', 'vegetable', 'fruit', 'bread', 'bakery']):
#                 print(f"Categorized {item_name} as DAILY (category: {category_name})")
#                 return 'DAILY'
#             elif any(cat in category_name for cat in ['meat', 'protein', 'frozen', 'refrigerated', 'cheese']):
#                 print(f"Categorized {item_name} as WEEKLY (category: {category_name})")
#                 return 'WEEKLY'
#             elif any(cat in category_name for cat in ['pantry', 'dry goods', 'spice', 'condiment', 'oil', 'grain', 'flour']):
#                 print(f"Categorized {item_name} as MONTHLY (category: {category_name})")
#                 return 'MONTHLY'
        
#         # Method 2: Use expiry date patterns from inventory items
#         expiry_days = calculate_average_expiry_days(item_name, inventory_items)
        
#         if expiry_days:
#             print(f"Item: {item_name}, Expiry days: {expiry_days}")
#             if expiry_days <= 7:  # Expires within a week
#                 return 'DAILY'
#             elif expiry_days <= 30:  # Expires within a month
#                 return 'WEEKLY'
#             else:  # Long shelf life
#                 return 'MONTHLY'
        
#         # Method 3: Fallback - be more generous with categorization
#         print(f"Using fallback categorization for: {item_name}")
        
#         # If no category or expiry data, use simple name-based heuristics
#         item_lower = item_name.lower()
        
#         # Daily items (perishables)
#         if any(word in item_lower for word in ['milk', 'bread', 'egg', 'yogurt', 'banana', 'apple', 'lettuce', 'tomato']):
#             return 'DAILY'
        
#         # Weekly items (proteins, some produce)
#         if any(word in item_lower for word in ['chicken', 'beef', 'fish', 'meat', 'cheese', 'onion', 'potato']):
#             return 'WEEKLY'
        
#         # Default to MONTHLY
#         return 'MONTHLY'
        
#     except Exception as e:
#         print(f"Error categorizing {item_name}: {e}")
#         return 'MONTHLY'


def categorize_by_inventory_data(item_name: str, inventory_items: List[Dict]) -> str:
    """Categorize based on actual inventory category and expiry patterns"""
    
    # Find matching inventory item
    matching_item = None
    for inv_item in inventory_items:
        if inv_item.get('itemName') == item_name:
            matching_item = inv_item
            break
    
    if not matching_item:
        print(f"❌ No inventory match found for: {item_name}")
        return 'MONTHLY'
    
    try:
        # Debug: Print full item structure for fruits
        if any(fruit in item_name.lower() for fruit in ['apple', 'banana', 'orange', 'grape', 'berry']):
            print(f"🍎 FRUIT DEBUG - {item_name}:")
            print(f"   Full item data: {matching_item}")
        
        # Method 1: Use inventory category if available
        category_info = matching_item.get('category', {})
        category_name = category_info.get('name', '').lower() if category_info else ''
        
        print(f"📦 Item: {item_name}, Category: '{category_name}'")
        
        if category_name:
            # Map inventory categories to shopping frequencies
            if any(cat in category_name for cat in ['dairy', 'fresh', 'produce', 'vegetable', 'fruit', 'bread', 'bakery']):
                print(f"✅ Categorized {item_name} as DAILY (category: {category_name})")
                return 'DAILY'
            elif any(cat in category_name for cat in ['meat', 'protein', 'frozen', 'refrigerated', 'cheese']):
                print(f"✅ Categorized {item_name} as WEEKLY (category: {category_name})")
                return 'WEEKLY'
            elif any(cat in category_name for cat in ['pantry', 'dry goods', 'spice', 'condiment', 'oil', 'grain', 'flour']):
                print(f"✅ Categorized {item_name} as MONTHLY (category: {category_name})")
                return 'MONTHLY'
            else:
                print(f"⚠️ Unknown category '{category_name}' for {item_name}")
        else:
            print(f"⚠️ No category found for {item_name}")
        
        # Method 2: Use expiry date patterns from inventory items
        expiry_days = calculate_average_expiry_days(item_name, inventory_items)
        
        if expiry_days:
            print(f"📅 Item: {item_name}, Expiry days: {expiry_days}")
            if expiry_days <= 7:
                print(f"✅ Categorized {item_name} as DAILY (expiry: {expiry_days} days)")
                return 'DAILY'
            elif expiry_days <= 30:
                print(f"✅ Categorized {item_name} as WEEKLY (expiry: {expiry_days} days)")
                return 'WEEKLY'
            else:
                print(f"✅ Categorized {item_name} as MONTHLY (expiry: {expiry_days} days)")
                return 'MONTHLY'
        else:
            print(f"⚠️ No expiry data found for {item_name}")
        
        # Method 3: Fallback - name-based heuristics
        print(f"🔄 Using fallback categorization for: {item_name}")
        
        item_lower = item_name.lower()
        
        # Daily items (perishables) - be more specific for fruits
        if any(word in item_lower for word in ['milk', 'bread', 'egg', 'yogurt']):
            print(f"✅ Fallback: {item_name} → DAILY (dairy/bakery)")
            return 'DAILY'
        
        # Fruits should ALWAYS be DAILY
        if any(fruit in item_lower for fruit in ['apple', 'banana', 'orange', 'grape', 'berry', 'fruit', 'mango', 'pear']):
            print(f"🍎 Fallback: {item_name} → DAILY (fruit)")
            return 'DAILY'
        
        # Vegetables should ALWAYS be DAILY
        if any(veg in item_lower for veg in ['lettuce', 'tomato', 'cucumber', 'carrot', 'spinach', 'vegetable']):
            print(f"🥬 Fallback: {item_name} → DAILY (vegetable)")
            return 'DAILY'
        
        # Weekly items
        if any(word in item_lower for word in ['chicken', 'beef', 'fish', 'meat', 'cheese', 'onion', 'potato']):
            print(f"✅ Fallback: {item_name} → WEEKLY (protein/staple)")
            return 'WEEKLY'
        
        # Default to MONTHLY
        print(f"⚠️ Fallback: {item_name} → MONTHLY (default)")
        return 'MONTHLY'
        
    except Exception as e:
        print(f"❌ Error categorizing {item_name}: {e}")
        return 'MONTHLY'

def calculate_average_expiry_days(item_name: str, inventory_items: List[Dict]) -> Optional[int]:
    """Calculate average days to expiry for similar items"""
    
    try:
        expiry_days = []
        current_date = datetime.now()
        
        for inv_item in inventory_items:
            if inv_item.get('itemName') == item_name:
                # Check if there are inventory items with expiry dates
                items = inv_item.get('items', [])
                for item in items:
                    expiry_date_str = item.get('expiryDate')
                    if expiry_date_str:
                        try:
                            expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
                            days_to_expiry = (expiry_date - current_date).days
                            if days_to_expiry > 0:  # Only future expiry dates
                                expiry_days.append(days_to_expiry)
                        except:
                            continue
        
        return int(np.mean(expiry_days)) if expiry_days else None
        
    except Exception as e:
        return None

def categorize_by_consumption_frequency(item_name: str, consumption_events: List[Dict]) -> str:
    """Fallback categorization based on consumption patterns"""
    
    item_events = [e for e in consumption_events if e.get('itemName') == item_name]
    
    if not item_events:
        return 'MONTHLY'
    
    try:
        dates = []
        for event in item_events:
            try:
                date_str = event['consumedAt']
                if isinstance(date_str, str):
                    if 'T' in date_str:
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        date_obj = datetime.fromisoformat(date_str)
                else:
                    date_obj = date_str
                dates.append(date_obj)
            except:
                continue
        
        if len(dates) < 2:
            return 'MONTHLY'
        
        dates.sort()
        intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
        avg_interval = sum(intervals) / len(intervals)
        
        if avg_interval <= 3:
            return 'DAILY'
        elif avg_interval <= 10:
            return 'WEEKLY'
        else:
            return 'MONTHLY'
            
    except Exception as e:
        return 'MONTHLY'

class ConsumptionData(BaseModel):
    consumptionEvents: List[Dict[str, Any]]
    currentInventory: List[Dict[str, Any]]
    kitchenId: int
    analysisStartDate: str

class SuggestionRequest(BaseModel):
    kitchenId: int
    listType: str
    existingItems: List[str]
    consumptionData: Optional[ConsumptionData] = None

@router.post("/suggestions")
async def get_ai_suggestions(request: SuggestionRequest) -> Dict[str, Any]:
    try:
        print(f"Processing request for kitchen {request.kitchenId}, list type: {request.listType}")
        
        if request.listType == "RANDOM":
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(f"http://localhost:8080/api/shopping-lists/low-stock/{request.kitchenId}")
                    if response.status_code == 200:
                        low_stock_items = response.json()
                        suggestions = convert_low_stock_to_suggestions(low_stock_items, request.existingItems)
                        print(f"Generated {len(suggestions)} low stock suggestions")
                    else:
                        suggestions = []
                except Exception as e:
                    print(f"Error fetching low stock items: {e}")
                    suggestions = []
        else:
            if request.consumptionData and request.consumptionData.consumptionEvents:
                suggestions = analyze_consumption_by_inventory_data(
                    request.consumptionData.dict(), 
                    request.listType, 
                    request.existingItems
                )
            else:
                suggestions = []
            
    except Exception as e:
        print(f"Error in analysis: {e}")
        suggestions = []
    
    print(f"Returning {len(suggestions)} suggestions")
    return {"suggestions": suggestions}

def analyze_consumption_by_inventory_data(consumption_data, list_type, existing_items):
    """Analyze using inventory categories and expiry data"""
    
    events = consumption_data['consumptionEvents']
    inventory = consumption_data['currentInventory']
    
    if not events:
        return []
    
    try:
        df = pd.DataFrame(events)
        df['consumedAt'] = pd.to_datetime(df['consumedAt'])
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1)
        
        cutoff_date = datetime.now() - timedelta(days=60)
        df = df[df['consumedAt'] >= cutoff_date]
        
        if df.empty:
            return []
        
        print(f"Analyzing {len(df)} events using inventory-based categorization")
        print(f"Looking for {list_type} items")
        
        suggestions = []
        inventory_dict = {item['itemName']: item for item in inventory}
        
        # Debug: Show some sample items
        sample_items = list(df['itemName'].unique())[:5]
        print(f"Sample consumed items: {sample_items}")
        
        # Analyze each consumed item
        daily_count = weekly_count = monthly_count = 0
        
        for item_name in df['itemName'].unique():
            if normalize_name(item_name) not in [normalize_name(x) for x in existing_items]:
                
                item_df = df[df['itemName'] == item_name]
                
                # Categorize using inventory data
                item_category = categorize_by_inventory_data(item_name, inventory)
                
                # Count categories for debugging
                if item_category == 'DAILY':
                    daily_count += 1
                elif item_category == 'WEEKLY':
                    weekly_count += 1
                elif item_category == 'MONTHLY':
                    monthly_count += 1
                
                # Only suggest items that match the requested list type
                if item_category == list_type:
                    
                    consumption_events = len(item_df)
                    days_since_last = (datetime.now() - item_df['consumedAt'].max().to_pydatetime()).days
                    
                    # More lenient suggestion criteria
                    should_suggest = False
                    if list_type == 'DAILY' and (days_since_last <= 14 or consumption_events >= 3):
                        should_suggest = True
                    elif list_type == 'WEEKLY' and (days_since_last <= 30 or consumption_events >= 2):
                        should_suggest = True
                    elif list_type == 'MONTHLY' and consumption_events >= 1:
                        should_suggest = True
                    
                    if should_suggest:
                        suggestion = create_inventory_based_suggestion(
                            item_name, 
                            inventory_dict.get(item_name), 
                            list_type,
                            consumption_events,
                            days_since_last
                        )
                        if suggestion:
                            suggestions.append(suggestion)
                            print(f"Added suggestion: {item_name} ({item_category})")
        
        print(f"Category distribution - Daily: {daily_count}, Weekly: {weekly_count}, Monthly: {monthly_count}")
        
        # Sort by consumption frequency
        suggestions.sort(key=lambda x: x.get('consumption_events', 0), reverse=True)
        
        # Limit results
        limits = {'DAILY': 8, 'WEEKLY': 10, 'MONTHLY': 12}
        suggestions = suggestions[:limits.get(list_type, 8)]
        
        print(f"Generated {len(suggestions)} inventory-based suggestions for {list_type}")
        return suggestions
        
    except Exception as e:
        print(f"Error in inventory-based analysis: {e}")
        return []

def create_inventory_based_suggestion(item_name, inventory_item, list_type, consumption_events, days_since_last):
    """Create suggestion using inventory data"""
    
    try:
        current_stock = inventory_item['currentQuantity'] if inventory_item else 0
        min_stock = inventory_item.get('minStock', 5) if inventory_item else 5
        
        suggested_quantity = max(min_stock - current_stock, 1)
        
        if current_stock >= min_stock:
            return None
        
        unit = inventory_item.get('unit', 'pieces') if inventory_item else 'pieces'
        suggested_quantity = min(suggested_quantity, 20)
        
        # Generate reason based on category
        category_name = inventory_item.get('category', {}).get('name', 'item') if inventory_item else 'item'
        reason = f"{list_type.lower()} {category_name.lower()} - low stock (current: {current_stock}, min: {min_stock})"
        
        return {
            'name': item_name,
            'quantity': int(suggested_quantity),
            'unit': unit,
            'reason': reason,
            'consumption_events': consumption_events,
            'days_since_last': days_since_last
        }
        
    except Exception as e:
        print(f"Error creating suggestion for {item_name}: {e}")
        return None

def convert_low_stock_to_suggestions(low_stock_items: List[Dict], existing_items: List[str]) -> List[Dict]:
    """Convert low stock items to suggestion format"""
    normalized_existing = [normalize_name(item) for item in existing_items]
    
    suggestions = []
    for item in low_stock_items:
        item_name = item.get('name', '')
        if item_name and normalize_name(item_name) not in normalized_existing:
            current_qty = item.get('currentQuantity', 0)
            min_stock = item.get('minStock', 5)
            suggested_qty = max(min_stock - current_qty, 1)
            
            suggestions.append({
                "name": item_name,
                "quantity": min(suggested_qty, 20),
                "unit": item.get('unit', 'pieces'),
                "reason": f"Low stock - current: {current_qty}, minimum: {min_stock}"
            })
    
    return suggestions

@router.post("/analyze-consumption")
async def analyze_consumption_endpoint(request: Dict[str, Any]) -> Dict[str, Any]:
    try:
        consumption_events = request.get("consumptionEvents", [])
        
        if not consumption_events:
            return {
                "analysisType": "NO_DATA",
                "totalEvents": 0,
                "insights": ["No consumption data available"]
            }
        
        df = pd.DataFrame(consumption_events)
        df['consumedAt'] = pd.to_datetime(df['consumedAt'])
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1)
        
        # Get inventory data for categorization
        inventory_data = request.get("currentInventory", [])
        
        categories = {'DAILY': 0, 'WEEKLY': 0, 'MONTHLY': 0}
        for item in df['itemName'].unique():
            category = categorize_by_inventory_data(item, inventory_data)
            categories[category] += 1
        
        return {
            "analysisType": "INVENTORY_BASED_CATEGORIZATION",
            "totalEvents": len(consumption_events),
            "uniqueItems": df['itemName'].nunique(),
            "analysisStartDate": df['consumedAt'].min().isoformat(),
            "analysisEndDate": df['consumedAt'].max().isoformat(),
            "itemsByCategory": categories,
            "topConsumedItems": df.groupby('itemName')['quantity'].sum().nlargest(5).to_dict(),
            "insights": [
                f"Analyzed {len(consumption_events)} consumption events",
                f"Found {df['itemName'].nunique()} unique items",
                f"Daily items: {categories['DAILY']}, Weekly: {categories['WEEKLY']}, Monthly: {categories['MONTHLY']}",
                "Using inventory categories and expiry data for categorization"
            ]
        }
        
    except Exception as e:
        print(f"Error in consumption analysis: {e}")
        return {
            "analysisType": "ERROR",
            "error": str(e),
            "insights": ["Unable to analyze consumption patterns"]
        }
