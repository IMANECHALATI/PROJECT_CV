from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, session
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
import cv2
import numpy as np
from collections import Counter
from datetime import datetime
import time
import json
import os
import hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = "smartresto_secret_key"

# ============================================
# CONFIGURATION
# ============================================
EMOTION_MODEL = "Emotion_little_vgg.h5"
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
EMOTIONS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
USERS_FILE = "users.json"
REPORTS_FILE = "reports_data.json"

APP_SETTINGS = {
    "sensitivity": 5,
    "confidence": 70,
    "alerts_enabled": True,
    "alert_delay": 10
}

# ============================================
# GESTION UTILISATEURS
# ============================================
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ============================================
# GESTION RAPPORTS JSON
# ============================================
def load_reports():
    if os.path.exists(REPORTS_FILE):
        with open(REPORTS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_report(report_data):
    reports = load_reports()
    reports.append(report_data)
    with open(REPORTS_FILE, 'w') as f:
        json.dump(reports, f, indent=4)

# ============================================
# LOGIQUE DE STATISTIQUES
# ============================================
class EmotionStats:
    def __init__(self):
        self.reset()

    def reset(self):
        self.total_customers = 0
        self.current_max_faces = 0
        self.total_frames = 0
        self.emotion_counts = Counter()
        self.last_face_time = 0
        self.angry_start_time = None
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
            if num_faces > self.current_max_faces:
                self.current_max_faces = num_faces

    def get_display_customers(self):
        return self.total_customers + self.current_max_faces

    def add_detection(self, emotion, confidence):
        self.total_frames += 1
        self.emotion_counts[emotion] += 1

        conf_threshold = APP_SETTINGS["confidence"] / 100.0

        if APP_SETTINGS["alerts_enabled"] and emotion == "angry" and confidence > conf_threshold:
            if self.angry_start_time is None:
                self.angry_start_time = time.time()
            elif time.time() - self.angry_start_time > APP_SETTINGS["alert_delay"]:
                if not self.is_alerting:
                    self.is_alerting = True
                    self.alerts_count += 1
                    self.alert_triggered = True
                    return True
        else:
            if emotion != "angry" or confidence <= conf_threshold or not APP_SETTINGS["alerts_enabled"]:
                self.angry_start_time = None
                self.is_alerting = False
                self.alert_triggered = False

        return False

    def get_satisfaction_score(self):
        if self.total_frames == 0:
            return 0
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
# CAMERA
# ============================================
def get_camera():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
    return camera

def generate_frames():
    global current_emotion
    model = load_model(EMOTION_MODEL)

    while True:
        cam = get_camera()
        success, frame = cam.read()
        if not success:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = FACE_CASCADE.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=int(APP_SETTINGS["sensitivity"]),
            minSize=(40, 40)
        )

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
            cv2.putText(frame, f"{emotion.upper()}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# ============================================
# ROUTES AUTH
# ============================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = load_users()

        if username in users:
            return render_template('register.html', error="Nom d'utilisateur déjà pris.")

        users[username] = hash_password(password)
        save_users(users)
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = load_users()

        if username in users and users[username] == hash_password(password):
            session['user'] = username
            return redirect(url_for('dashboard'))

        return render_template('login.html', error="Identifiants incorrects.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# ============================================
# ROUTES PRINCIPALES
# ============================================
@app.route('/')
def index():
    return render_template("Acceuil.html")

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route('/reports')
@login_required
def reports():
    return render_template("reports.html")

@app.route('/settings')
@login_required
def settings():
    return render_template("settings.html")

@app.route('/video_feed')
@login_required
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

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
    if total_cust > 0:
        save_report({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "customers": total_cust,
            "satisfaction": stats.get_satisfaction_score(),
            "alerts": stats.alerts_count
        })
    stats.reset()
    return jsonify({"status": "success"})

@app.route('/api/report')
@login_required
def api_report():
    reports = load_reports()
    if not reports:
        return jsonify({"weekly_trend": [], "daily_data": []})
    recent = reports[-7:] if len(reports) > 7 else reports
    return jsonify({
        "weekly_trend": [{"day": r["date"].split(" ")[1], "satisfaction": r["satisfaction"]} for r in recent],
        "daily_data": list(reversed(reports))
    })

@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    return jsonify(APP_SETTINGS)

@app.route('/api/settings', methods=['POST'])
@login_required
def update_settings():
    global APP_SETTINGS
    data = request.json
    APP_SETTINGS["sensitivity"] = int(data.get("sensitivity", 5))
    APP_SETTINGS["confidence"] = int(data.get("confidence", 70))
    APP_SETTINGS["alerts_enabled"] = bool(data.get("alerts_enabled", True))
    APP_SETTINGS["alert_delay"] = int(data.get("alert_delay", 10))
    return jsonify({"status": "success", "settings": APP_SETTINGS})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)