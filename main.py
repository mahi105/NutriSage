import os
import logging
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from utils.nutrition import get_food_analysis, generate_recommendations, analyze_food_for_chat

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat_message():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'response': 'Please ask me about a specific food!'}), 400

        response = analyze_food_for_chat(user_message)
        return jsonify({'response': response})

    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return jsonify({'response': 'Sorry, I had trouble processing that request. Please try again.'}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Get form data
        age = int(request.form.get('age'))
        weight = float(request.form.get('weight'))
        height = float(request.form.get('height'))
        gender = request.form.get('gender')
        activity_level = request.form.get('activity_level')
        goal = request.form.get('goal')
        dietary_restrictions = request.form.getlist('dietary_restrictions')

        # Calculate BMR and daily calorie needs
        if gender == 'male':
            bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
        else:
            bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)

        activity_multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'very': 1.725,
            'extra': 1.9
        }

        daily_calories = bmr * activity_multipliers[activity_level]

        # Adjust calories based on goal
        if goal == 'lose':
            daily_calories -= 500
        elif goal == 'gain':
            daily_calories += 500

        # Get food recommendations
        recommendations = generate_recommendations(
            daily_calories,
            dietary_restrictions,
            goal
        )

        return render_template(
            'results.html',
            daily_calories=round(daily_calories),
            recommendations=recommendations
        )

    except Exception as e:
        logger.error(f"Error processing nutrition analysis: {str(e)}")
        flash("An error occurred while processing your request. Please try again.", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)