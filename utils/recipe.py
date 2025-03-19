import os
import requests
import re
from typing import Dict, Optional

THEMEALDB_API_URL = "https://www.themealdb.com/api/json/v1/1/search.php"

def clean_instructions(raw_instructions: str) -> list:
    steps = [step.strip() for step in raw_instructions.split('\r\n') if step.strip()]
    
    has_numbering = any(re.match(r'^\d+\.(\d+)?\s', step) for step in steps)
    
    cleaned_steps = []
    if has_numbering:
        for step in steps:
            cleaned_step = re.sub(r'^\d+\.\d+\.\s*', '', step)  
            cleaned_step = re.sub(r'^\d+\.\d+\s*', '', cleaned_step) 
            cleaned_step = re.sub(r'^\d+\.\s*', '', cleaned_step) 
            cleaned_step = re.sub(r'^\d+\s+', '', cleaned_step)  
            cleaned_steps.append(cleaned_step.strip())
    else:
        cleaned_steps = steps
    
    return cleaned_steps

def generate_recipe(dish_type: str, preferences: list = None) -> Optional[Dict]:
    try:
        params = {'s': dish_type}
        response = requests.get(THEMEALDB_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if not data.get('meals'):
            print(f"No recipes found for: {dish_type}")
            return None
        meal = data['meals'][0]
        ingredients = []
        for i in range(1, 21):
            ingredient = meal.get(f'strIngredient{i}')
            measure = meal.get(f'strMeasure{i}')
            if ingredient and ingredient.strip():
                ingredients.append(f"{measure} {ingredient}".strip())
        if preferences:
            for pref in preferences:
                if pref == 'vegetarian' and any('meat' in i.lower() or 'chicken' in i.lower() for i in ingredients):
                    print(f"Recipe excluded due to {pref} preference")
                    return None
                if pref == 'vegan' and any('egg' in i.lower() or 'milk' in i.lower() for i in ingredients):
                    print(f"Recipe excluded due to {pref} preference")
                    return None
                if pref == 'gluten_free' and 'flour' in ' '.join(ingredients).lower():
                    print(f"Recipe excluded due to {pref} preference")
                    return None
        raw_instructions = meal.get('strInstructions', '')
        instructions = clean_instructions(raw_instructions)
        return {
            'title': meal.get('strMeal', dish_type),
            'ingredients': ingredients,
            'instructions': instructions,
            'tips': None
        }
    except requests.exceptions.RequestException as e:
        print(f"Error generating recipe: {str(e)}")
        return None