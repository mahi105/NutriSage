import os
import requests
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

USDA_API_KEY = os.environ.get("USDA_API_KEY")
USDA_API_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

def get_food_analysis(food_query: str) -> Optional[Dict]:
    """
    Get nutrition information for a food item from USDA API
    """
    try:
        # Add logging to debug API calls
        logger.debug(f"Searching for food: {food_query}")

        response = requests.get(
            f"{USDA_API_BASE_URL}/foods/search",
            params={
                "api_key": USDA_API_KEY,
                "query": food_query,
                "pageSize": 5,  # Get more results to find better matches
                "dataType": ["Survey (FNDDS)"],  # Focus on standard food database
                "sortBy": "dataType.keyword",
                "sortOrder": "asc"
            }
        )
        response.raise_for_status()
        data = response.json()

        if not data.get('foods'):
            logger.debug(f"No foods found for query: {food_query}")
            return None

        # Try to find an exact match first
        for food in data['foods']:
            description = food.get('description', '').lower()
            if food_query.lower() in description:
                logger.debug(f"Found matching food: {food['description']}")
                return food

        # If no exact match, return the first result
        logger.debug(f"No exact match found, using first result: {data['foods'][0]['description']}")
        return data['foods'][0]

    except requests.exceptions.RequestException as e:
        logger.error(f"USDA API request failed: {str(e)}")
        return None

def analyze_food_for_chat(food_query: str) -> str:
    """
    Analyze food and return a chatbot-friendly response
    """
    food_data = get_food_analysis(food_query)

    if not food_data:
        return f"I couldn't find nutritional information for {food_query}. Could you try being more specific? For example, instead of 'orange', try 'fresh orange' or 'orange fruit'."

    # Extract key nutrients
    nutrients = food_data.get('foodNutrients', [])
    nutrient_dict = {}

    for nutrient in nutrients:
        name = nutrient.get('nutrientName', '').lower()
        value = nutrient.get('value', 0)

        if 'protein' in name:
            nutrient_dict['protein'] = value
        elif 'carbohydrate' in name and 'by difference' in name:
            nutrient_dict['carbs'] = value
        elif 'total lipid (fat)' in name:
            nutrient_dict['fat'] = value
        elif 'energy' in name:
            nutrient_dict['calories'] = value

    # Generate response
    response = f"Here's what I found about {food_data.get('description', food_query)}:\n\n"
    response += f"• Calories: {nutrient_dict.get('calories', 0):.1f} kcal\n"
    response += f"• Protein: {nutrient_dict.get('protein', 0):.1f}g\n"
    response += f"• Carbs: {nutrient_dict.get('carbs', 0):.1f}g\n"
    response += f"• Fat: {nutrient_dict.get('fat', 0):.1f}g\n\n"

    # Add simple advice
    calories = nutrient_dict.get('calories', 0)
    protein = nutrient_dict.get('protein', 0)

    if calories < 100:
        response += "This is a low-calorie food, good for weight management! "
    elif calories > 300:
        response += "This is a calorie-dense food, be mindful of portion sizes. "

    if protein > 10:
        response += "It's a good source of protein! "

    # Add serving size information if available
    serving_size = food_data.get('servingSize')
    serving_unit = food_data.get('servingSizeUnit')
    if serving_size and serving_unit:
        response += f"\n\nNutritional values are based on a {serving_size}{serving_unit} serving."

    return response

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