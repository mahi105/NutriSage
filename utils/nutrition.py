import os
import requests
from typing import List, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

USDA_API_KEY = os.environ.get("USDA_API_KEY")
USDA_API_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

def clean_food_query(query: str) -> str:
    question_words = r'\b(what|should|how|about|can|i|eat|have|tell|me)\b'
    query = re.sub(question_words, '', query.lower())
    query = re.sub(r'[?.!]', '', query)
    return query.strip()

def split_food_query(query: str) -> List[str]:
    query = clean_food_query(query)
    split_patterns = r'(?:and|,|\s+with\s+|\s+&\s+)'
    items = re.split(split_patterns, query.lower())
    return [item.strip() for item in items if item.strip()]

def get_food_analysis(food_query: str) -> Optional[Dict]:
    try:
        food_query = clean_food_query(food_query)
        logger.debug(f"Searching for food: {food_query}")

        response = requests.get(
            f"{USDA_API_BASE_URL}/foods/search",
            params={
                "api_key": USDA_API_KEY,
                "query": food_query,
                "pageSize": 5, 
                "dataType": ["Survey (FNDDS)"], 
                "sortBy": "dataType.keyword",
                "sortOrder": "asc"
            }
        )
        response.raise_for_status()
        data = response.json()

        if not data.get('foods'):
            logger.debug(f"No foods found for query: {food_query}")
            return None

        query_terms = set(food_query.split())
        best_match = None
        highest_match_score = 0

        for food in data['foods']:
            description = food.get('description', '').lower()
            desc_terms = set(description.split())

            common_terms = query_terms.intersection(desc_terms)
            match_score = len(common_terms) / len(query_terms)

            if food_query in description:
                match_score += 1

            if any(word in description.lower() for word in ['raw', 'fresh', 'natural']):
                match_score += 0.5

            if any(word in description.lower() for word in ['candy', 'processed', 'artificial']):
                match_score -= 0.5

            if match_score > highest_match_score:
                highest_match_score = match_score
                best_match = food
                logger.debug(f"Found better match: {food['description']} (score: {match_score})")

        if best_match and highest_match_score > 0.3: 
            return best_match

        logger.debug(f"No good match found for: {food_query}")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"USDA API request failed: {str(e)}")
        return None

def analyze_food_for_chat(food_query: str) -> str:
    food_items = split_food_query(food_query)

    if len(food_items) > 1:
        responses = []
        food_data_list = []

        for item in food_items:
            food_data = get_food_analysis(item)
            if food_data:
                food_data_list.append(food_data)
                responses.append(format_food_analysis(food_data))

        if not responses:
            return f"I couldn't find nutritional information for any of these foods. Could you try being more specific?"

        combined_response = "<br><br>".join(responses)
        if len(food_data_list) > 1:
            pairing_advice = analyze_food_pairing(food_data_list)
            combined_response += f"<hr><br>{pairing_advice}"

        return combined_response
    else:
        food_data = get_food_analysis(food_query)
        if not food_data:
            return f"I couldn't find nutritional information for {food_query}. Could you try being more specific? For example, instead of 'orange', try 'fresh orange' or 'orange fruit'."

        return format_food_analysis(food_data)

def format_food_analysis(food_data: Dict) -> str:
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

    food_name = food_data.get('description', '')
    calories = nutrient_dict.get('calories', 0)
    protein = nutrient_dict.get('protein', 0)
    carbs = nutrient_dict.get('carbs', 0)
    fat = nutrient_dict.get('fat', 0)
    serving_size = food_data.get('servingSize')
    serving_unit = food_data.get('servingSizeUnit')

    response = f"Hi there! Let’s dive into the nutrition profile of <span class='food-name'>{food_name}</span>. Here’s what I’ve got for you:<br><br>"
    response += "<strong>Nutritional Breakdown</strong><br>"
    response += "<ul>"
    response += f"<li>Calories: {calories:.1f} kcal</li>"
    response += f"<li>Protein: {protein:.1f}g</li>"
    response += f"<li>Carbohydrates: {carbs:.1f}g</li>"
    response += f"<li>Fat: {fat:.1f}g</li>"
    response += "</ul><br>"

    if serving_size and serving_unit:
        response += f"<i>Based on a {serving_size}{serving_unit} serving.</i><br><br>"

    response += "<strong>Health Insights</strong><br>"
    response += "<ul>"
    if 'coconut milk' in food_name.lower():
        response += "<li>Supports Heart Health: The healthy fats (like medium-chain triglycerides) in coconut milk can boost HDL (good cholesterol) levels.</li>"
        response += "<li>Boosts Immunity: Contains lauric acid, which has antimicrobial properties to support your immune system.</li>"
        if calories < 100:
            response += "<li>Weight-Friendly: With its low calorie count, it’s a great addition to lighter meals or smoothies!</li>"
    elif 'fish curry' in food_name.lower():
        response += "<li>Rich in Omega-3s: Fish is packed with omega-3 fatty acids, fantastic for heart and brain health.</li>"
        response += "<li>Muscle Support: The protein content helps repair and build muscle tissue—perfect after a workout.</li>"
        if calories < 100:
            response += "<li>Light Yet Nourishing: Low in calories but high in nutrients, it’s a balanced choice for any meal.</li>"
    elif 'pie, lemon' in food_name.lower():
        response += "<li>Energy Booster: Those carbs provide a solid source of fuel for your day.</li>"
        response += "<li>Satisfying Fats: Higher fat content can keep you fuller longer—just watch portions!</li>"
    elif 'chicken, chicken roll, roasted' in food_name.lower():
        response += "<li>Muscle Builder: High protein content makes this a great choice for muscle repair and growth.</li>"
        response += "<li>Low-Carb Friendly: Perfect if you’re watching your carb intake.</li>"
    else:
        if protein > 10:
            response += "<li>Muscle Builder: High protein content makes this a great choice for muscle repair and growth.</li>"
        elif protein > 5:
            response += "<li>Steady Energy: A decent protein level helps keep you full and energized.</li>"
        if carbs > 20:
            response += "<li>Energy Booster: Those carbs provide a solid source of fuel for your day.</li>"
        elif carbs < 5:
            response += "<li>Low-Carb Friendly: Perfect if you’re watching your carb intake.</li>"
        if fat > 10:
            response += "<li>Satisfying Fats: Higher fat content can keep you fuller longer—just watch portions!</li>"
        elif fat < 5:
            response += "<li>Heart-Healthy: Low fat makes this a lighter option for cardiovascular wellness.</li>"
        if calories < 100:
            response += "<li>Weight Management Ally: Low calories make it easy to fit into a balanced diet.</li>"
        elif calories > 300:
            response += "<li>Energy Dense: Great for fueling active days, but moderation is key.</li>"
    response += "</ul><br>"

    response += "<strong>Nutritionist Tip</strong><br>"
    if 'coconut milk' in food_name.lower():
        response += "Try using coconut milk in moderation—pair it with spices like turmeric or ginger for a flavorful, anti-inflammatory boost!"
    elif 'fish curry' in food_name.lower():
        response += "Opt for a side of steamed veggies with your fish curry to round out the meal with fiber and micronutrients."
    elif 'pie, lemon' in food_name.lower():
        response += "Consider adding a lean protein source to this for a more complete meal."
    elif 'chicken, chicken roll, roasted' in food_name.lower():
        response += "Pair this with a fiber-rich veggie to balance your plate and keep digestion on track."
    else:
        if protein > 5:
            response += "Pair this with a fiber-rich veggie to balance your plate and keep digestion on track."
        else:
            response += "Consider adding a lean protein source to this for a more complete meal."

    return response

def analyze_food_pairing(foods: List[Dict]) -> str:
    food_names = [food.get('description', '').lower() for food in foods]

    incompatible_pairs = [
        (['milk', 'dairy'], ['fish', 'seafood']),  
        (['citrus', 'orange', 'lemon'], ['milk', 'dairy']), 
        (['iron', 'spinach', 'lentils'], ['calcium', 'milk', 'cheese', 'yogurt']),  
        (['coffee', 'tea'], ['iron', 'spinach', 'red meat']),  
        (['banana', 'potato', 'starchy'], ['citrus', 'orange', 'pineapple']),  
        (['milk', 'dairy'], ['raw egg', 'egg']),  
        (['alcohol', 'beer', 'wine'], ['protein', 'chicken', 'fish']),  
        (['sugar', 'candy', 'sweets'], ['protein', 'meat', 'tofu']),  
        (['fatty', 'oil', 'fried'], ['cold', 'ice cream', 'soda']),  
        (['cucumber', 'raw vegetables'], ['milk', 'dairy']),  
    ]

    for group1, group2 in incompatible_pairs:
        if (any(term in ' '.join(food_names) for term in group1) and 
            any(term in ' '.join(food_names) for term in group2)):
            return "⚠️ Note: These foods might not be the best combination for optimal nutrition absorption. Consider eating them separately."

    total_calories = sum(
        next((n['value'] for n in food.get('foodNutrients', []) 
              if n.get('nutrientName', '').lower() == 'energy'), 0)
        for food in foods
    )

    if total_calories < 300:
        return "✅ These foods make a healthy, low-calorie combination!"
    else:
        return "✅ These foods can be eaten together. Just be mindful of portion sizes as the total calories add up."

def generate_recommendations(
    daily_calories: float,
    dietary_restrictions: List[str],
    goal: str
) -> Dict:
    if goal == 'lose':
        protein_ratio = 0.40
        carb_ratio = 0.30
        fat_ratio = 0.30
    elif goal == 'gain':
        protein_ratio = 0.30
        carb_ratio = 0.50
        fat_ratio = 0.20
    else:
        protein_ratio = 0.30
        carb_ratio = 0.40
        fat_ratio = 0.30

    protein_calories = daily_calories * protein_ratio
    carb_calories = daily_calories * carb_ratio
    fat_calories = daily_calories * fat_ratio

    protein_grams = protein_calories / 4
    carb_grams = carb_calories / 4
    fat_grams = fat_calories / 9

    suggested_foods = []

    protein_sources = ["chicken breast", "salmon", "eggs", "tofu"]
    carb_sources = ["brown rice", "quinoa", "sweet potato", "oats"]
    fat_sources = ["avocado", "olive oil", "nuts", "seeds"]

    if 'vegetarian' in dietary_restrictions:
        protein_sources = ["tofu", "lentils", "chickpeas", "tempeh"]

    if 'vegan' in dietary_restrictions:
        protein_sources = ["tofu", "lentils", "chickpeas", "tempeh"]
        fat_sources = ["avocado", "olive oil", "nuts", "seeds"]

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