# import os
# import requests
# from flask import Flask, render_template, request, jsonify
# from dotenv import load_dotenv
# import openai
# from flask_cors import CORS
# load_dotenv()

# app = Flask(__name__)
# CORS(app)  

# GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')
# OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# openai.api_key = OPENAI_API_KEY

# GOOGLE_PLACES_ENDPOINT = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/search-restaurants', methods=['POST'])
# def search_restaurants():
#     try:
#         data = request.json
#         city = data.get('city')
#         preferences = data.get('preferences')

#         if not city or not preferences:
#             return jsonify({'error': 'City and preferences are required'}), 400

#         places_response = fetch_restaurants_from_google(city)

#         if 'error' in places_response:
#             return jsonify({'error': 'Error fetching data from Google Places'}), 500

#         restaurants = places_response.get('results', [])

#         refined_results = refine_restaurants_with_openai(restaurants, preferences)

#         return jsonify(refined_results), 200
#     except Exception as e:
#         print(f"Error: {e}")  
#         return jsonify({'error': 'Internal server error occurred'}), 500
# def fetch_restaurants_from_google(city):
#     params = {
#         'query': f'restaurants in {city}',
#         'key': GOOGLE_PLACES_API_KEY,
#         'type': 'restaurant'
#     }
#     response = requests.get(GOOGLE_PLACES_ENDPOINT, params=params)
#     if response.status_code == 200:
#         return response.json()
#     else:
#         return {'error': 'Failed to retrieve data from Google Places'}

# def refine_restaurants_with_openai(restaurants, preferences):
#     try:
#         restaurant_descriptions = [
#             f"{restaurant['name']}: {restaurant['formatted_address']}, {restaurant.get('types', [])}, {restaurant.get('rating', 'No rating')} rating, {restaurant.get('user_ratings_total', 0)} reviews"
#             for restaurant in restaurants
#         ]

#         prompt = f"Given the following list of restaurants, identify which ones are most likely to be {preferences} friendly based on their descriptions and reviews, consider the type drinks and if they would be appropriate for tha preference: {restaurant_descriptions}"

#         response = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system", "content": "You are a helpful assistant that refines restaurant suggestions based on preferences."},
#                 {"role": "user", "content": prompt}
#             ],
#             max_tokens=150,
#             temperature=0.7
#         )

#         filtered_restaurants = response['choices'][0]['message']['content'].strip().split('\n')
#         print(f"OpenAI Response: {response}")  
#         return {"filtered_restaurants": filtered_restaurants}
#     except Exception as e:
#         print(f"Error in OpenAI API call: {e}")
#         return {"error": "Failed to refine results with OpenAI"}

# if __name__ == '__main__':
#     app.run(debug=True)
from flask import Flask, render_template, request, jsonify
import os
import base64
import io
import requests
from PIL import Image
import pytesseract

app = Flask(__name__)

# Replace this with your actual Google Cloud Vision API Key
GOOGLE_CLOUD_API_KEY = "YOUR_API_KEY_HERE"
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/api/process-image', methods=['POST'])
def process_image():
    if 'image' not in request.json:
        return jsonify({"error": "No image provided"}), 400

    image_data = request.json['image']
    image_bytes = base64.b64decode(image_data)

    try:
        # Step 1: Perform OCR using Tesseract
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        print("OCR Text recognized:", text)

        # Step 2: Perform object detection using Google Vision API
        vision_url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_CLOUD_API_KEY}"
        vision_payload = {
            "requests": [
                {
                    "image": {"content": image_data},
                    "features": [{"type": "OBJECT_LOCALIZATION"}]
                }
            ]
        }
        vision_response = requests.post(vision_url, json=vision_payload)
        vision_response.raise_for_status()
        vision_data = vision_response.json()
        
        objects = vision_data['responses'][0].get('localizedObjectAnnotations', [])
        print("Google Vision Objects:", objects)

        # Combine OCR and object detection results
        product_info = extract_product_info(text, objects)
        print("Extracted Product Info:", product_info)

        return jsonify({
            "text": text,
            "objects": objects,
            "productInfo": product_info
        })

    except Exception as e:
        print('Error processing image:', str(e))
        return jsonify({"error": str(e)}), 500

def extract_product_info(text, objects):
    product_info = {
        "name": "",
        "brand": "",
        "model": "",
        "size": "",
    }

    print("Extracting product info from OCR text...")
    lines = text.split('\n')
    for line in lines:
        if any(size in line.lower() for size in ["inch", '"']):
            product_info["size"] = line.strip()
        elif "model:" in line.lower():
            product_info["model"] = line.replace("model:", "", 1).strip()
        elif not product_info["name"]:
            product_info["name"] = line.strip()

    print("Using object detection to refine product name...")
    if objects:
        product_info["name"] = objects[0]['name']

    brand_match = product_info["name"].split()
    if brand_match:
        product_info["brand"] = brand_match[0]

    print("Product Info extracted:", product_info)
    return product_info

if __name__ == '__main__':
    app.run(debug=True)