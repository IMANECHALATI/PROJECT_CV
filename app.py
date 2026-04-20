from flask import Flask, render_template, Response, jsonify, request, session, redirect, url_for
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from collections import Counter
from datetime import datetime
import time
import json
import os
import hashlib
from functools import wraps
import smtplib
from email.message import EmailMessage
import threading

app = Flask(__name__)
app.secret_key = 'smartresto_super_secret_key'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============================================
# CONFIGURATION & REGLAGES DYNAMIQUES
# ============================================
EMOTION_MODEL = "Emotion_little_vgg.h5"
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
EMOTIONS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
REPORTS_FILE = "reports_data.json"
USERS_FILE = "users.json"

# DICTIONNAIRE COMPLET (Corrige l'erreur 500 Serveur)
APP_SETTINGS = {
    "sensitivity": 5,
    "confidence": 70,
    "alerts_enabled": True,
    "alert_delay": 10,
    "scan_mode": "deep",
    "surveillance_mode": "standard",
    "camera_source": "0",
    "save_alert_file": False,
    "report_format": "narratif",
    "data_retention": "never"
}

# ============================================
# FONCTIONS AUTHENTIFICATION
# ============================================
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f: return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f: json.dump(users, f, indent=4)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# GESTION DES RAPPORTS & AUTO-DELETE (RGPD)
# ============================================
def load_reports():
    if os.path.exists(REPORTS_FILE):
        with open(REPORTS_FILE, 'r') as f: return json.load(f)
    return []

def save_report(report_data):
    reports = load_reports()
    reports.append(report_data)

    retention = APP_SETTINGS.get("data_retention", "never")
    if retention != "never":
        now = datetime.now()
        valid_reports = []
        for r in reports:
            try:
                r_date = datetime.strptime(r["date"], "%Y-%m-%d %H:%M")
                diff_seconds = (now - r_date).total_seconds()
                if retention == "24h" and diff_seconds <= 86400:
                    valid_reports.append(r)
                elif retention == "7d" and diff_seconds <= 604800:
                    valid_reports.append(r)
            except:
                valid_reports.append(r)
        reports = valid_reports

    with open(REPORTS_FILE, 'w') as f: json.dump(reports, f, indent=4)

# ============================================
# ENVOI D'EMAIL EN ARRIERE-PLAN (ALERTE)
# ============================================
def send_email_async(destinataire):
    try:
        EMAIL_ADDRESS = "oumaima1272005@gmail.com" # <--- METS TON EMAIL ICI
        EMAIL_PASSWORD = "ttmbvxissncypvua" # <--- TON CODE D'APPLICATION GMAIL

        msg = EmailMessage()
        msg['Subject'] = "🚨 Chalil AI : Alerte de Mécontentement Client !"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = destinataire
        msg.set_content(f"""
Bonjour,

Le système SmartResto vient de détecter un client en colère dans votre établissement.
L'alerte a été déclenchée le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}.

Veuillez vérifier le Dashboard ou la salle pour intervenir rapidement.

Cordialement,
L'équipe SmartResto
        """)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print(f"✅ Email envoyé avec succès à {destinataire}")
    except Exception as e:
        print(f"❌ Erreur email : {e}")

# ============================================
# LOGIQUE DE STATISTIQUES (IA) AVEC TOLERANCE
# ============================================
class EmotionStats:
    def __init__(self): self.reset()

    def reset(self):
        self.total_customers = 0
        self.current_max_faces = 0
        self.total_frames = 0
        self.emotion_counts = Counter()
        self.last_face_time = 0
        self.angry_start_time = None
        self.last_angry_time = 0
        self.alert_triggered = False
        self.alerts_count = 0
        self.is_alerting = False

    def update_frame_faces(self, num_faces):
        current_time = time.time()
        if current_time - self.last_face_time > 3.0:
            self.total_customers += self.current_max_faces
            self.current_max_faces = 0
        if num_faces > 0:
            self.last_face_time = current_time
            if num_faces > self.current_max_faces: self.current_max_faces = num_faces

    def get_display_customers(self):
        return self.total_customers + self.current_max_faces

    def add_detection(self, emotion, confidence):
        self.total_frames += 1
        self.emotion_counts[emotion] += 1
        
        alert_delay = APP_SETTINGS.get("alert_delay", 10)
        if APP_SETTINGS.get("surveillance_mode", "standard") == "strict": alert_delay = 4
        elif APP_SETTINGS.get("surveillance_mode", "standard") == "tolerant": alert_delay = 20
        
        conf_threshold = APP_SETTINGS.get("confidence", 70) / 100.0
        current_time = time.time()

        if APP_SETTINGS.get("alerts_enabled", True) and emotion == "angry" and confidence > conf_threshold:
            self.last_angry_time = current_time 
            if self.angry_start_time is None:
                self.angry_start_time = current_time
            elif current_time - self.angry_start_time > alert_delay:
                if not self.is_alerting:
                    self.is_alerting = True
                    self.alerts_count += 1
                    self.alert_triggered = True
                return True 
        else:
            # Tolérance de 2.5 secondes (Filtre Anti-Clignotement)
            if self.angry_start_time is not None and (current_time - self.last_angry_time > 2.5):
                self.angry_start_time = None
                self.is_alerting = False
                self.alert_triggered = False
            
            if self.is_alerting: return True
                
        return False

    def get_satisfaction_score(self):
        if self.total_frames == 0: return 0
        good = self.emotion_counts["happy"] + self.emotion_counts["neutral"]
        return int((good / self.total_frames) * 100)

    def get_stats(self):
        data = {}
        for emotion in EMOTIONS:
            count = self.emotion_counts[emotion]
            percentage = round((count / self.total_frames) * 100, 1) if self.total_frames > 0 else 0
            data[emotion] = {"count": count, "percentage": percentage}
        return data

stats = EmotionStats()
camera = None
current_emotion = {"emotion": "neutral", "confidence": 0, "face_detected": False, "alert": False}

# ============================================
# CAMERA ET VIDEO EN BOUCLE
# ============================================
def get_camera():
    global camera
    if camera is None:
        src = APP_SETTINGS["camera_source"]
        cam_index = int(src) if src.isdigit() else src
        camera = cv2.VideoCapture(cam_index)
    return camera

def generate_frames():
    global current_emotion
    model = load_model(EMOTION_MODEL)

    while True:
        cam = get_camera()
        success, frame = cam.read()
        
        if not success:
            src = str(APP_SETTINGS["camera_source"])
            if not src.isdigit() and not src.startswith("http"):
                cam.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "ERREUR CAMERA (IP / Tel deconnecte)", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(1)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        scale_factor = 1.1 if APP_SETTINGS["scan_mode"] == "deep" else 1.3
        
        faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=scale_factor, minNeighbors=int(APP_SETTINGS["sensitivity"]), minSize=(40, 40))

        current_emotion["face_detected"] = len(faces) > 0
        stats.update_frame_faces(len(faces))
        current_emotion["alert"] = False

        for (x, y, w, h) in faces:
            roi = gray[y:y+h, x:x+w]
            roi = cv2.resize(roi, (48, 48))
            roi = roi.astype("float") / 255.0
            roi = img_to_array(roi)
            roi = np.expand_dims(roi, axis=0)

            prediction = model.predict(roi, verbose=0)[0]
            emotion = EMOTIONS[np.argmax(prediction)]
            confidence = float(np.max(prediction))

            current_emotion["emotion"] = emotion
            current_emotion["confidence"] = confidence

            if stats.add_detection(emotion, confidence): 
                current_emotion["alert"] = True

            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 255, 255), 2)
            cv2.putText(frame, f"{emotion.upper()} {int(confidence*100)}%", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# ============================================
# ROUTES AUTHENTIFICATION (LOGIN/REGISTER)
# ============================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email') 
        password = request.form.get('password')
        
        users = load_users()
        if username in users: 
            return render_template('register.html', error="Nom d'utilisateur déjà pris.")
        
        users[username] = {"password": hash_password(password), "email": email}
        save_users(users)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = load_users()
        
        if username in users:
            user_data = users[username]
            # CORRECTION : Accepte les anciens comptes sans email et les nouveaux
            stored_pwd = user_data if isinstance(user_data, str) else user_data.get("password")
            
            if stored_pwd == hash_password(password):
                session['user'] = username
                return redirect(url_for('dashboard'))
            
        return render_template('login.html', error="Identifiants incorrects.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# ============================================
# ROUTES PRINCIPALES (PAGES)
# ============================================
@app.route('/')
def index(): return render_template("Acceuil.html")
@app.route('/dashboard')
@login_required
def dashboard(): return render_template("dashboard.html")
@app.route('/reports')
@login_required
def reports(): return render_template("reports.html")
@app.route('/settings')
@login_required
def settings(): return render_template("settings.html")
@app.route('/video_feed')
@login_required
def video_feed(): return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ============================================
# ROUTES API
# ============================================
@app.route('/api/stats')
@login_required
def api_stats():
    return jsonify({
        "total_customers": stats.get_display_customers(), 
        "emotions": stats.get_stats(), 
        "satisfaction_score": stats.get_satisfaction_score(), 
        "current_emotion": current_emotion
    })

@app.route('/api/reset_stats', methods=['POST'])
@login_required
def reset_stats():
    global stats
    total_cust = stats.get_display_customers()
    summary_text = ""

    if total_cust > 0:
        satisfaction = stats.get_satisfaction_score()
        alerts = stats.alerts_count
        save_report({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "customers": total_cust,
            "satisfaction": satisfaction,
            "alerts": alerts
        })

        format_type = APP_SETTINGS.get("report_format", "standard")
        if format_type == "narratif":
            qualif = "excellent" if satisfaction >= 80 else "moyen" if satisfaction >= 50 else "difficile"
            summary_text = f"📝 Bilan Narratif : Service {qualif} aujourd'hui avec {satisfaction}% de satisfaction globale pour {total_cust} clients analysés. L'équipe a dû gérer {alerts} alertes de mécontentement."
        elif format_type == "alertes":
            summary_text = f"⚠️ Bilan Alertes : {alerts} incidents de mécontentement enregistrés."
        else:
            summary_text = f"📊 Bilan Standard : Clients: {total_cust} | Satisfaction: {satisfaction}% | Alertes: {alerts}."

    stats.reset()
    return jsonify({"status": "success", "summary": summary_text})

@app.route('/api/report')
@login_required
def api_report():
    reports = load_reports()
    if not reports: return jsonify({"weekly_trend": [], "daily_data": []})
    recent = reports[-7:] if len(reports) > 7 else reports
    return jsonify({"weekly_trend": [{"day": r["date"].split(" ")[1], "satisfaction": r["satisfaction"]} for r in recent], "daily_data": list(reversed(reports))})

@app.route('/api/upload_video', methods=['POST'])
@login_required
def upload_video():
    if 'video_file' in request.files:
        file = request.files['video_file']
        if file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            return jsonify({"status": "success", "filepath": filepath})
    return jsonify({"status": "error"})

@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings(): return jsonify(APP_SETTINGS)

@app.route('/api/settings', methods=['POST'])
@login_required
def update_settings():
    global APP_SETTINGS, camera
    data = request.json
    
    new_camera_source = data.get("camera_source", "0")
    if APP_SETTINGS.get("camera_source") != new_camera_source:
        if camera is not None:
            camera.release()
            camera = None
            
    APP_SETTINGS["camera_source"] = new_camera_source
    APP_SETTINGS["sensitivity"] = int(data.get("sensitivity", 5))
    APP_SETTINGS["confidence"] = int(data.get("confidence", 70))
    APP_SETTINGS["alerts_enabled"] = bool(data.get("alerts_enabled", True))
    APP_SETTINGS["alert_delay"] = int(data.get("alert_delay", 10))
    APP_SETTINGS["scan_mode"] = data.get("scan_mode", "deep")
    APP_SETTINGS["surveillance_mode"] = data.get("surveillance_mode", "standard")
    APP_SETTINGS["save_alert_file"] = bool(data.get("save_alert_file", False))
    APP_SETTINGS["report_format"] = data.get("report_format", "narratif")
    APP_SETTINGS["data_retention"] = data.get("data_retention", "never")
    
    return jsonify({"status": "success", "settings": APP_SETTINGS})

@app.route('/api/send_alert_email', methods=['POST'])
@login_required
def api_send_alert_email():
    print("🔔 --- DEMANDE D'ENVOI D'EMAIL REÇUE DEPUIS LE DASHBOARD ---")
    users = load_users()
    username = session.get('user')
    
    print(f"👤 Utilisateur connecté : {username}")
    
    if username and username in users:
        user_data = users[username]
        
        # Vérifie si le compte a un email
        user_email = user_data.get('email') if isinstance(user_data, dict) else None
        print(f"📧 Email trouvé dans la base de données : {user_email}")
        
        if user_email:
            print("🚀 Tout est bon, lancement de l'envoi en arrière-plan...")
            threading.Thread(target=send_email_async, args=(user_email,)).start()
            return jsonify({"status": "success", "message": "Email déclenché"})
        else:
            print("❌ ERREUR : Cet utilisateur n'a pas d'adresse email enregistrée !")
            
    return jsonify({"status": "error", "message": "Email introuvable"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)