from fastapi import APIRouter, HTTPException
from app.models.advanced_recipe import AdvancedRecipeRequest, AdvancedRecipeResponse
from app.services.advanced_recipe_service import AdvancedRecipeService

router = APIRouter(prefix="/ai", tags=["advanced_recipes"])
advanced_recipe_service = AdvancedRecipeService()

print("🔥 [PYTHON] Advanced recipes router loaded!")

@router.post("/advanced-recipes", response_model=AdvancedRecipeResponse)
async def generate_advanced_recipes(request: AdvancedRecipeRequest):
    print("🚨 [PYTHON] /ai/advanced-recipes endpoint called!")
    print(f"🔥 [PYTHON] ENDPOINT HIT - ADVANCED RECIPES")
    try:
        print(f"🍳 [PYTHON] Advanced recipe generation for {len(request.items)} items")
        print(f"📋 [PYTHON] Recipe type: {request.recipe_type}")
        print(f"📋 [PYTHON] Recipe type TYPE: {type(request.recipe_type)}")
        print(f"⏱️ [PYTHON] Max cooking time: {request.max_cooking_time}")
        print(f"👤 [PYTHON] User ID: {request.user_id}")
        print(f"🎯 [PYTHON] Servings: {request.servings}")
        print(f"🔍 [PYTHON] RAW REQUEST DATA:")
        print(f"  recipe_type: {request.recipe_type}")
        print(f"  max_cooking_time: {request.max_cooking_time}")
        print(f"  servings: {request.servings}")
        print(f"  user_id: {request.user_id}")
        print("=" * 80)
        
        if request.expiring_items:
            print(f"⏰ [PYTHON] Expiring items: {[item.name for item in request.expiring_items]}")
        
        if request.preferences:
            print(f"⚙️ [PYTHON] User preferences: skill={request.preferences.skill_level}, max_time={request.preferences.max_cooking_time}")
        
        result = await advanced_recipe_service.generate_advanced_recipes(request)
        
        print(f"✅ [PYTHON] Generated {len(result.recipes)} advanced recipes")
        print(f"🎯 [PYTHON] Recipe type: {result.recipe_type}")
        
        if result.expiring_items_used:
            print(f"♻️ [PYTHON] Expiring items used: {result.expiring_items_used}")
        
        return result
        
    except Exception as e:
        print(f"❌ [PYTHON] Error generating advanced recipes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/expiry-recipes", response_model=AdvancedRecipeResponse)
async def generate_expiry_recipes(request: AdvancedRecipeRequest):
    print("🚨 [PYTHON] /ai/expiry-recipes endpoint called!")
    print(f"⏰ [PYTHON] DEDICATED EXPIRY RECIPES ENDPOINT")
    print(f"⏰ [PYTHON] Expiring items count: {len(request.expiring_items) if request.expiring_items else 0}")
    try:
        print(f"⏰ [PYTHON] Expiry-based recipe generation")
        
        # Force recipe type to expiry-based
        request.recipe_type = "EXPIRY_BASED"
        
        result = await advanced_recipe_service.generate_advanced_recipes(request)
        print(f"✅ [PYTHON] Generated {len(result.recipes)} expiry-based recipes")
        
        return result
        
    except Exception as e:
        print(f"❌ [PYTHON] Error generating expiry recipes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quick-recipes", response_model=AdvancedRecipeResponse)
async def generate_quick_recipes(request: AdvancedRecipeRequest):
    print("🚨 [PYTHON] /ai/quick-recipes endpoint called!")
    print(f"⚡ [PYTHON] DEDICATED QUICK RECIPES ENDPOINT")
    print(f"⚡ [PYTHON] MaxCookingTime from request: {request.maxCookingTime}")
    try:
        print(f"⚡ [PYTHON] Quick recipe generation")
        
        # Force recipe type to quick
        request.recipe_type = "QUICK"
        
        result = await advanced_recipe_service.generate_advanced_recipes(request)
        print(f"✅ [PYTHON] Generated {len(result.recipes)} quick recipes")
        
        return result
        
    except Exception as e:
        print(f"❌ [PYTHON] Error generating quick recipes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/wastage-prevention", response_model=AdvancedRecipeResponse)
async def generate_wastage_prevention_recipes(request: AdvancedRecipeRequest):
    try:
        print(f"♻️ [PYTHON] Wastage prevention recipe generation")
        
        # Force recipe type to wastage prevention
        request.recipe_type = "WASTAGE_PREVENTION"
        
        result = await advanced_recipe_service.generate_advanced_recipes(request)
        print(f"✅ [PYTHON] Generated {len(result.recipes)} wastage prevention recipes")
        
        return result
        
    except Exception as e:
        print(f"❌ [PYTHON] Error generating wastage prevention recipes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))