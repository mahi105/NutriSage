import os
import requests
from typing import List, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

USDA_API_KEY = os.environ.get("USDA_API_KEY")
USDA_API_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

def clean_food_query(query: str) -> str:
    """
    Clean up the food query by removing question words and common filler words
    """
    # Remove question words and filler words
    question_words = r'\b(what|should|how|about|can|i|eat|have|tell|me)\b'
    query = re.sub(question_words, '', query.lower())
    # Remove punctuation except commas (used for separating foods)
    query = re.sub(r'[?.!]', '', query)
    return query.strip()

def split_food_query(query: str) -> List[str]:
    """
    Split a compound food query into individual food items
    """
    query = clean_food_query(query)
    # Split on common conjunctions and punctuation
    split_patterns = r'(?:and|,|\s+with\s+|\s+&\s+)'
    items = re.split(split_patterns, query.lower())
    # Clean up and remove empty items
    return [item.strip() for item in items if item.strip()]

def get_food_analysis(food_query: str) -> Optional[Dict]:
    """
    Get nutrition information for a food item from USDA API
    """
    try:
        # Clean up the query
        food_query = clean_food_query(food_query)
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

        # Try to find the best match
        query_terms = set(food_query.split())
        best_match = None
        highest_match_score = 0

        for food in data['foods']:
            description = food.get('description', '').lower()
            desc_terms = set(description.split())

            # Calculate match score based on word overlap
            common_terms = query_terms.intersection(desc_terms)
            match_score = len(common_terms) / len(query_terms)

            # Boost score if it's an exact phrase match
            if food_query in description:
                match_score += 1

            # Boost score for raw/fresh foods over processed ones
            if any(word in description.lower() for word in ['raw', 'fresh', 'natural']):
                match_score += 0.5

            # Penalize scores for obviously wrong matches
            if any(word in description.lower() for word in ['candy', 'processed', 'artificial']):
                match_score -= 0.5

            if match_score > highest_match_score:
                highest_match_score = match_score
                best_match = food
                logger.debug(f"Found better match: {food['description']} (score: {match_score})")

        if best_match and highest_match_score > 0.3:  # Only use matches with decent confidence
            return best_match

        # If no good match found, return None to trigger a more specific request
        logger.debug(f"No good match found for: {food_query}")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"USDA API request failed: {str(e)}")
        return None

def analyze_food_for_chat(food_query: str) -> str:
    """
    Analyze food and return a chatbot-friendly response
    """
    # Split compound queries
    food_items = split_food_query(food_query)

    if len(food_items) > 1:
        # Handle multiple food items
        responses = []
        for item in food_items:
            food_data = get_food_analysis(item)
            if food_data:
                responses.append(format_food_analysis(food_data))

        if not responses:
            return f"I couldn't find nutritional information for any of these foods. Could you try being more specific?"

        return "\n\n=====\n\n".join(responses)
    else:
        # Single food item
        food_data = get_food_analysis(food_query)
        if not food_data:
            return f"I couldn't find nutritional information for {food_query}. Could you try being more specific? For example, instead of 'orange', try 'fresh orange' or 'orange fruit'."

        return format_food_analysis(food_data)

def format_food_analysis(food_data: Dict) -> str:
    """
    Format food analysis data into a readable response
    """
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
    response = f"Here's what I found about {food_data.get('description', '')}:\n\n"
    response += f"• Calories: {nutrient_dict.get('calories', 0):.1f} kcal\n"
    response += f"• Protein: {nutrient_dict.get('protein', 0):.1f}g\n"
    response += f"• Carbs: {nutrient_dict.get('carbs', 0):.1f}g\n"
    response += f"• Fat: {nutrient_dict.get('fat', 0):.1f}g\n\n"

    # Add nutritional advice
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