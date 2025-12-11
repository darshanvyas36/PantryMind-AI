from fastapi import APIRouter, HTTPException
from app.models.recipe import RecipeRequest, RecipeResponse
from app.services.recipe_service import RecipeService
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/ai", tags=["recipes"])
recipe_service = RecipeService()

class RecipeByNameRequest(BaseModel):
    recipeName: str
    servings: int = 4
    availableItems: List[dict]

@router.post("/recipes", response_model=RecipeResponse)
async def generate_recipes(request: RecipeRequest, category: str = None):
    print("🍳 [PYTHON] /ai/recipes endpoint called!")
    if category:
        print(f"🏷️ [PYTHON] Category-specific recipes requested: {category}")
    try:
        print(f"🍳 [PYTHON] Generating recipes for {request.servings} people")
        print(f"📦 [PYTHON] Available items: {[item.name for item in request.items]}")
        print(f"🏷️ [PYTHON] Category: {category if category else 'General'}")
        
        result = recipe_service.generate_recipes(request, category)
        
        print(f"✅ [PYTHON] Generated {len(result.recipes)} recipes successfully")
        return result
    except Exception as e:
        print(f"❌ [PYTHON] Error generating recipes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recipe-by-name", response_model=RecipeResponse)
async def generate_recipe_by_name(request: RecipeByNameRequest):
    print(f"🍳 [PYTHON] /ai/recipe-by-name endpoint called!")
    print(f"📝 [PYTHON] Recipe name: {request.recipeName}")
    print(f"👥 [PYTHON] Servings: {request.servings}")
    print(f"📦 [PYTHON] Available items: {len(request.availableItems)}")
    
    try:
        result = recipe_service.generate_recipe_by_name(request)
        print(f"✅ [PYTHON] Generated recipe for: {request.recipeName}")
        return result
    except Exception as e:
        print(f"❌ [PYTHON] Error generating recipe by name: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))