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
from werkzeug.utils import secure_filename 

# 1. Ortam değişkenlerini yükle
load_dotenv()

app = Flask(__name__)

# GÜVENLİK YAMASI 2: CORS Kısıtlaması
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost"]}})

# GÜVENLİK YAMASI 1.1: Maksimum Dosya Boyutu (5 MB)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

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

# --- HIBRIT AI YAPILANDIRMASI ---
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

# GÜVENLİK YAMASI 1.2: Dosya uzantısı kontrol fonksiyonu
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

# --- HIBRIT AI MOTORU ---
def get_ai_estimation(damage_description, image_base64):
    try:
        image_bytes = base64.b64decode(image_base64)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                f"Analyze this vehicle damage technically. Identify specific issues. User description: {damage_description}",
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            ]
        )
        
        perceived_data = response.text if response.text else damage_description

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
    
    # GÜVENLİK YAMASI 4: Girdi Doğrulaması
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({"msg": "Kullanıcı adı ve şifre boş bırakılamaz"}), 400
    if len(username) < 3 or len(username) > 50:
        return jsonify({"msg": "Kullanıcı adı 3-50 karakter arasında olmalıdır"}), 400
    if len(password) < 6:
        return jsonify({"msg": "Şifre en az 6 karakter olmalıdır"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Kullanıcı adı zaten mevcut"}), 400
        
    new_user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"msg": "Kayıt başarılı"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    if user and check_password_hash(user.password_hash, data.get('password')):
        return jsonify(access_token=create_access_token(identity=str(user.id)))
    return jsonify({"msg": "Hatalı kullanıcı adı veya şifre"}), 401

@app.route('/api/analyze', methods=['POST'])
@jwt_required()
def analyze():
    current_user_id = get_jwt_identity()
    
    # GÜVENLİK YAMASI 1.3: Dosya Varlığı ve Türü Kontrolü
    if 'file' not in request.files: 
        return jsonify({"error": "Dosya isteğe eklenmemiş"}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Seçili dosya yok"}), 400
        
    if not allowed_file(file.filename):
        return jsonify({"error": "Sadece JPG ve PNG dosyaları kabul edilmektedir"}), 400

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
        return jsonify({"error": "Analiz sırasında bir hata oluştu"}), 500

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
            
    # GÜVENLİK YAMASI 3: Debug Modunu kapattık
    is_debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(debug=is_debug, host='0.0.0.0', port=5000)