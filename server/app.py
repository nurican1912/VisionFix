import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Allow communication with React

# --- CONFIGURATION (BASED ON PDF) ---
# Endpoint URL from PDF
API_URL = "https://api-ap-southeast-1.modelarts-maas.com/v1/chat/completions"

# Your Token (Hardcoded to avoid .env issues)
API_TOKEN = "CcbRY-OG3iLi569ybZAIRscxj8pkfED6MflBbYY5pZt-tx_qFIqhadVXJ_-IAFInEAb1Q7R0vn0Kso8AVWOw2A"

# Model Name from PDF
MODEL_NAME = "qwen3-32b"

def get_ai_estimation(damage_description):
    """Sends a request to Huawei Cloud AI API"""
    
    # Header Structure (Authorization: Bearer)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_TOKEN}"
    }

    # System Prompt (Role assignment)
    system_instruction = (
        "You are an expert vehicle damage assessor. "
        "Analyze the user's description of the vehicle damage. "
        "Provide a estimated repair cost (in USD) and a list of parts to replace. "
        "Keep the response professional and concise."
    )

    # Request Body (JSON)
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": damage_description}
        ],
        "max_tokens": 1024,  # Recommended value
        "temperature": 0.3   # Low temperature for logical analysis
    }

    try:
        print(f"Calling AI Model ({MODEL_NAME})...")
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        
        # Print status to terminal
        print(f"API Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Extract content from response
            return data['choices'][0]['message']['content']
        else:
            print(f"ERROR: {response.text}")
            return f"AI Error: {response.status_code}"

    except Exception as e:
        print(f"Connection Error: {e}")
        return "Failed to connect to server."

@app.route('/api/analyze', methods=['POST'])
def analyze():
    # Handle request from Frontend (React)
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    # Get description text from React
    description = request.form.get('description', 'General damage analysis')
    
    # Call AI function
    ai_result = get_ai_estimation(description)
    
    return jsonify({
        "success": True,
        "report": ai_result
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)