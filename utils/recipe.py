import os
import requests
from typing import Dict, Optional

CHEFGPT_API_KEY = os.environ.get('CHEFGPT_API_KEY', 'c2da6a79-7dda-4f09-9aee-683c2dece34e')
CHEFGPT_API_URL = "https://api.chefgpt.xyz/v1/recipes"

def generate_recipe(dish_type: str, preferences: list = None) -> Optional[Dict]:
    """
    Generate a recipe using ChefGPT API
    """
    try:
        headers = {
            'Authorization': f'Bearer {CHEFGPT_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'dish': dish_type,
            'preferences': preferences or []
        }
        
        response = requests.post(CHEFGPT_API_URL, json=data, headers=headers)
        response.raise_for_status()
        
        recipe_data = response.json()
        return {
            'title': recipe_data.get('title', dish_type),
            'ingredients': recipe_data.get('ingredients', []),
            'instructions': recipe_data.get('instructions', []),
            'tips': recipe_data.get('tips')
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Error generating recipe: {str(e)}")
        return None
