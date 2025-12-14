# app/core/ai/converter.py
from typing import List
from datetime import date, timedelta
from app.core.ai.schemas import BillExtractionSchema, ProductDetectionSchema, LabelExtractionSchema
from app.models.common import ExtractedItem, StorageType
import logging

logger = logging.getLogger(__name__)

class SchemaConverter:
    """Convert Pydantic schemas to internal models"""
    
    @staticmethod
    def bill_schema_to_items(schema: BillExtractionSchema) -> List[ExtractedItem]:
        """Convert BillExtractionSchema to ExtractedItem list"""
        items = []
        
        for item_schema in schema.items:
            # Calculate expiry date from shelf_life_days
            expiry_date = None
            expiry_source = None
            
            if item_schema.shelf_life_days:
                today = date.today()
                expiry_date = today + timedelta(days=item_schema.shelf_life_days)
                expiry_source = "ai_predicted"
            
            # Convert storage_type to enum
            storage_type = StorageType.UNKNOWN
            if item_schema.storage_type:
                try:
                    storage_type = StorageType(item_schema.storage_type.lower())
                except ValueError:
                    storage_type = StorageType.UNKNOWN
            
            item = ExtractedItem(
                raw_name=item_schema.raw_name,
                canonical_name=item_schema.canonical_name,
                category=item_schema.category,
                brand=item_schema.brand,
                quantity=item_schema.quantity,
                unit=item_schema.unit,
                price=item_schema.price,
                expiry_date=expiry_date,
                expiry_source=expiry_source,
                storage_type=storage_type,
                is_food=item_schema.is_food,
                confidence=item_schema.confidence
            )
            items.append(item)
        
        logger.info(f"Converted {len(items)} bill items from schema")
        return items
    
    @staticmethod
    def product_schema_to_items(schema: ProductDetectionSchema) -> List[ExtractedItem]:
        """Convert ProductDetectionSchema to ExtractedItem list"""
        items = []
        
        for product_schema in schema.products:
            expiry_date = None
            expiry_source = None
            
            if product_schema.shelf_life_days:
                today = date.today()
                expiry_date = today + timedelta(days=product_schema.shelf_life_days)
                expiry_source = "ai_predicted"
            
            storage_type = StorageType.UNKNOWN
            if product_schema.storage_type:
                try:
                    storage_type = StorageType(product_schema.storage_type.lower())
                except ValueError:
                    storage_type = StorageType.UNKNOWN
            
            item = ExtractedItem(
                raw_name=product_schema.raw_name,
                canonical_name=product_schema.canonical_name,
                category=product_schema.category,
                brand=product_schema.brand,
                quantity=product_schema.quantity,
                unit=product_schema.unit,
                expiry_date=expiry_date,
                expiry_source=expiry_source,
                storage_type=storage_type,
                is_food=product_schema.is_food,
                confidence=product_schema.confidence
            )
            items.append(item)
        
        logger.info(f"Converted {len(items)} product items from schema")
        return items
    
    @staticmethod
    def label_schema_to_item(schema: LabelExtractionSchema) -> ExtractedItem:
        """Convert LabelExtractionSchema to ExtractedItem"""
        
        expiry_date = None
        expiry_source = None
        
        if schema.expiry_date:
            try:
                from datetime import datetime
                expiry_date = datetime.strptime(schema.expiry_date, '%Y-%m-%d').date()
                expiry_source = "explicit"
            except ValueError:
                pass
        
        if not expiry_date and schema.shelf_life_days:
            today = date.today()
            expiry_date = today + timedelta(days=schema.shelf_life_days)
            expiry_source = "ai_predicted"
        
        storage_type = StorageType.UNKNOWN
        if schema.storage_type:
            try:
                storage_type = StorageType(schema.storage_type.lower())
            except ValueError:
                storage_type = StorageType.UNKNOWN
        
        item = ExtractedItem(
            raw_name=schema.product_name,
            canonical_name=schema.canonical_name,
            category=schema.category,
            brand=schema.brand,
            quantity=schema.quantity,
            unit=schema.unit,
            expiry_date=expiry_date,
            expiry_source=expiry_source,
            storage_type=storage_type,
            is_food=schema.is_food,
            confidence=schema.confidence
        )
        
        logger.info(f"Converted label item from schema: {item.raw_name}")
        return item

schema_converter = SchemaConverter()