# app/core/tools/analytics_tool.py
from typing import Dict, Any, List
from .base_tool import BaseTool

class KitchenAnalyticsTool(BaseTool):
    """Tool for fetching kitchen analytics and insights"""
    
    @property
    def name(self) -> str:
        return "kitchen_analytics"
    
    @property
    def description(self) -> str:
        return "Get consumption patterns, trends, and analytics for a kitchen"
    
    async def _run(self, kitchen_id: int, time_period: str = "30") -> Dict[str, Any]:
        """
        Fetch analytics data from Java backend
        
        Args:
            kitchen_id: Kitchen ID to analyze
            time_period: Time period for analysis (days)
        """
        # Fetch different analytics endpoints
        analytics_data = {}
        
        endpoints = [
            ("usage", "/api/analytics/usage"),
            ("waste", "/api/analytics/waste"),
            ("purchases", "/api/analytics/purchases"),
            ("categories", "/api/analytics/categories"),
            ("summary", "/api/analytics/summary")
        ]
        
        for key, endpoint in endpoints:
            try:
                data = await self._make_api_call(f"{endpoint}/{kitchen_id}")
                analytics_data[key] = data
            except Exception as e:
                analytics_data[key] = {"error": str(e)}
        
        return {
            "kitchen_id": kitchen_id,
            "analytics": analytics_data,
            "insights": self._generate_insights(analytics_data)
        }
    
    def _generate_insights(self, data: Dict[str, Any]) -> List[str]:
        """Generate actionable insights from analytics data"""
        insights = []
        
        # Waste insights
        if "waste" in data and not data["waste"].get("error"):
            waste_data = data["waste"]
            if waste_data.get("totalWaste", 0) > 0:
                insights.append(f"You've wasted {waste_data.get('totalWaste', 0)} items recently")
        
        # Usage insights
        if "usage" in data and not data["usage"].get("error"):
            usage_data = data["usage"]
            if usage_data.get("mostUsedCategory"):
                insights.append(f"Your most used category is {usage_data['mostUsedCategory']}")
        
        return insights