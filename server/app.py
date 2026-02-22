import base64
import os
import time
import pyodbc
import requests
import urllib.parse
from google import genai
from google.genai import types
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

# 1. Ortam değişkenlerini yükle
load_dotenv()

app = Flask(__name__)
CORS(app)

# --- VERİTABANI YAPILANDIRMASI ---
server = os.getenv('DB_SERVER', 'mssql-service') 
database = os.getenv('DB_NAME', 'VisionFixDB')
username = os.getenv('DB_USER', 'sa')
password = os.getenv('DB_PASSWORD')

driver = '{ODBC Driver 17 for SQL Server}'
connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};'

params = urllib.parse.quote_plus(connection_string)
app.config['SQLALCHEMY_DATABASE_URI'] = "mssql+pyodbc:///?odbc_connect=%s" % params
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'VisionFix_2026_ADU_ComputerEngineering_Secret_Key') 

db = SQLAlchemy(app)
jwt = JWTManager(app)

# --- HIBRIT AI YAPILANDIRMASI (YENİ SDK) ---
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

HUAWEI_API_URL = os.getenv('HUAWEI_API_URL')
HUAWEI_TOKEN = os.getenv('HUAWEI_TOKEN')
HUAWEI_MODEL = os.getenv('HUAWEI_MODEL', 'deepseek-v3.1')

# --- VERİTABANI MODELLERİ ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Analysis(db.Model):
    __tablename__ = 'analyses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    ai_report = db.Column(db.Text, nullable=True)

# --- MSSQL BAŞLATMA ---
def initialize_database():
    master_conn_str = f'DRIVER={driver};SERVER={server};DATABASE=master;UID={username};PWD={password};'
    for i in range(15):
        try:
            print(f"[{i+1}/15] SQL Server bağlantısı deneniyor...")
            conn = pyodbc.connect(master_conn_str, autocommit=True, timeout=10)
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM sys.databases WHERE name = '{database}'")
            if not cursor.fetchone():
                print(f"Veritabanı oluşturuluyor: {database}")
                cursor.execute(f"CREATE DATABASE {database}")
            cursor.close()
            conn.close()
            print("Veritabanı başarıyla bağlandı.")
            return True
        except Exception as e:
            print(f"Hata: {e}. 5 saniye bekleniyor...")
            time.sleep(5)
    return False

# --- HIBRIT AI MOTORU (YENİ SDK MİMARİSİ) ---
def get_ai_estimation(damage_description, image_base64):
    try:
        # Adım 1: Gemini Perception (Yeni google-genai SDK kullanımı)
        image_bytes = base64.b64decode(image_base64)
        
        # HATA DÜZELTİLDİ: model="gemini-1.5-flash" yerine güncel model olan "gemini-2.5-flash" kullanıldı.
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                f"Analyze this vehicle damage technically. Identify specific issues. User description: {damage_description}",
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            ]
        )
        
        # Yanıtı alırken yeni yapıya uygun şekilde erişiyoruz
        perceived_data = response.text if response.text else damage_description

        # Adım 2: Huawei DeepSeek Reasoning
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {HUAWEI_TOKEN}"}
        payload = {
            "model": HUAWEI_MODEL,
            "messages": [
                {"role": "system", "content": "Sen araç hasar eksperisin. Gemini'den gelen teknik verilerle profesyonel USD maliyet raporu hazırla."},
                {"role": "user", "content": f"Teknik Veriler: {perceived_data}"}
            ]
        }
        h_res = requests.post(HUAWEI_API_URL, headers=headers, json=payload, timeout=60)
        
        if h_res.status_code == 200:
            return h_res.json()['choices'][0]['message']['content']
        return f"Maliyet çıkarılamadı (Huawei Hata). Teknik Tespit: {perceived_data}"

    except Exception as e:
        return f"Sistem hatası: {str(e)}"

# --- ENDPOINTS ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"msg": "Username mevcut"}), 400
    new_user = User(username=data['username'], password_hash=generate_password_hash(data['password']))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"msg": "Kayıt başarılı"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password_hash, data['password']):
        return jsonify(access_token=create_access_token(identity=str(user.id)))
    return jsonify({"msg": "Hatalı giriş"}), 401

@app.route('/api/analyze', methods=['POST'])
@jwt_required()
def analyze():
    current_user_id = get_jwt_identity()
    if 'file' not in request.files: return jsonify({"error": "Dosya eksik"}), 400
    file = request.files['file']
    description = request.form.get('description', 'Genel hasar analizi')
    
    try:
        file_bytes = file.read() 
        image_base64 = base64.b64encode(file_bytes).decode('utf-8')
        ai_result = get_ai_estimation(description, image_base64)
        
        new_analysis = Analysis(user_id=int(current_user_id), image_data=file_bytes, description=description, ai_report=ai_result)
        db.session.add(new_analysis)
        db.session.commit()
        return jsonify({"success": True, "report": ai_result})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/history', methods=['GET'])
@jwt_required()
def get_history():
    current_user_id = get_jwt_identity()
    user_analyses = Analysis.query.filter_by(user_id=int(current_user_id)).order_by(Analysis.id.desc()).all()
    history_data = [
        {
            "id": a.id, 
            "description": a.description, 
            "ai_report": a.ai_report, 
            "image": f"data:image/jpeg;base64,{base64.b64encode(a.image_data).decode('utf-8')}"
        } for a in user_analyses
    ]
    return jsonify(history_data)

if __name__ == '__main__':
    with app.app_context():
        if initialize_database():
            db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)