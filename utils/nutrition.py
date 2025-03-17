import os
import requests
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

USDA_API_KEY = os.environ.get("USDA_API_KEY", "DEMO_KEY")
USDA_API_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

def get_food_analysis(food_query: str) -> Dict:
    """
    Get nutrition information for a food item from USDA API
    """
    try:
        response = requests.get(
            f"{USDA_API_BASE_URL}/foods/search",
            params={
                "api_key": USDA_API_KEY,
                "query": food_query,
                "pageSize": 1
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get('foods'):
            return None
            
        return data['foods'][0]
    except requests.exceptions.RequestException as e:
        logger.error(f"USDA API request failed: {str(e)}")
        raise Exception("Failed to fetch nutrition data")

def generate_recommendations(
    daily_calories: float,
    dietary_restrictions: List[str],
    goal: str
) -> Dict:
    """
    Generate personalized food recommendations based on user inputs
    """
    # Calculate macronutrient ratios based on goal
    if goal == 'lose':
        protein_ratio = 0.40
        carb_ratio = 0.30
        fat_ratio = 0.30
    elif goal == 'gain':
        protein_ratio = 0.30
        carb_ratio = 0.50
        fat_ratio = 0.20
    else:  # maintain
        protein_ratio = 0.30
        carb_ratio = 0.40
        fat_ratio = 0.30
        
    # Calculate macro amounts in grams
    protein_calories = daily_calories * protein_ratio
    carb_calories = daily_calories * carb_ratio
    fat_calories = daily_calories * fat_ratio
    
    protein_grams = protein_calories / 4
    carb_grams = carb_calories / 4
    fat_grams = fat_calories / 9
    
    # Generate meal suggestions based on restrictions
    suggested_foods = []
    
    protein_sources = ["chicken breast", "salmon", "eggs", "tofu"]
    carb_sources = ["brown rice", "quinoa", "sweet potato", "oats"]
    fat_sources = ["avocado", "olive oil", "nuts", "seeds"]
    
    if 'vegetarian' in dietary_restrictions:
        protein_sources = ["tofu", "lentils", "chickpeas", "tempeh"]
    
    if 'vegan' in dietary_restrictions:
        protein_sources = ["tofu", "lentils", "chickpeas", "tempeh"]
        fat_sources = ["avocado", "olive oil", "nuts", "seeds"]
    
    # Get nutrition data for suggested foods
    for food in protein_sources[:2] + carb_sources[:2] + fat_sources[:2]:
        food_data = get_food_analysis(food)
        if food_data:
            suggested_foods.append(food_data)
    
    return {
        'macros': {
            'protein': round(protein_grams),
            'carbs': round(carb_grams),
            'fat': round(fat_grams)
        },
        'suggested_foods': suggested_foods
    }
