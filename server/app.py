import base64
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION (SQLite) ---
# Veritabanı dosyası 'instance' klasörü veya ana dizinde oluşacaktır.
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'visionfix.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'change-this-to-a-secure-secret-key'  # Security key

db = SQLAlchemy(app)
jwt = JWTManager(app)

# --- AI CONFIGURATION ---
API_URL = "https://api-ap-southeast-1.modelarts-maas.com/v1/chat/completions"
# Not: Token'ı güvenli tutmak normalde .env dosyasında olmalı ama şimdilik burada kalsın.
API_TOKEN = "CcbRY-OG3iLi569ybZAIRscxj8pkfED6MflBbYY5pZt-tx_qFIqhadVXJ_-IAFInEAb1Q7R0vn0Kso8AVWOw2A"
MODEL_NAME = "qwen3-32b"

# --- MODELS ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Analysis(db.Model):
    __tablename__ = 'analyses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # SQLite'da LargeBinary BLOB olarak tutulur
    image_data = db.Column(db.LargeBinary, nullable=False)
    description = db.Column(db.String, nullable=True)
    ai_report = db.Column(db.String, nullable=True)

# --- AI FUNCTION ---
def get_ai_estimation(damage_description):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_TOKEN}"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are an expert vehicle damage assessor. Provide a repair cost estimate in USD and parts list based on the description."},
            {"role": "user", "content": damage_description}
        ],
        "max_tokens": 1024,
        "temperature": 0.3
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return f"AI Error: {response.status_code}"
    except Exception as e:
        return "Failed to connect to AI server."

# --- ENDPOINTS ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"msg": "Username already exists"}), 400
    
    hashed_pw = generate_password_hash(data['password'])
    new_user = User(username=data['username'], password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"msg": "Registration successful"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    
    if user and check_password_hash(user.password_hash, data['password']):
        access_token = create_access_token(identity=str(user.id))
        return jsonify(access_token=access_token)
    
    return jsonify({"msg": "Invalid username or password"}), 401

@app.route('/api/analyze', methods=['POST'])
@jwt_required()
def analyze():
    current_user_id = get_jwt_identity()
    
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    description = request.form.get('description', 'General damage analysis')
    
    # AI Analysis
    ai_result = get_ai_estimation(description)
    
    # Save to Database
    new_analysis = Analysis(
        user_id=current_user_id,
        image_data=file.read(),
        description=description,
        ai_report=ai_result
    )
    db.session.add(new_analysis)
    db.session.commit()
    
    return jsonify({"success": True, "report": ai_result})

# --- VERİTABANI OLUŞTURMA ---
# Uygulama her başladığında tabloları kontrol eder, yoksa oluşturur.
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)