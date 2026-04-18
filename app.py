from flask import Flask, render_template, Response, jsonify, request
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
import cv2
import numpy as np
from collections import Counter, deque
from datetime import datetime
import time
import json
import os

app = Flask(__name__)

# ============================================
# CONFIGURATION & REGLAGES DYNAMIQUES
# ============================================
EMOTION_MODEL = "Emotion_little_vgg.h5"
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
EMOTIONS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
REPORTS_FILE = "reports_data.json"

# Les paramètres modifiables depuis la page Settings
APP_SETTINGS = {
    "sensitivity": 5,        # minNeighbors pour OpenCV (1-10)
    "confidence": 70,        # Pourcentage de certitude
    "alerts_enabled": True,  # Activer/Désactiver les alertes
    "alert_delay": 10        # Secondes avant déclenchement
}

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
        
        # Récupère les paramètres actuels
        conf_threshold = APP_SETTINGS["confidence"] / 100.0
        
        # Logique d'alerte dynamique
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
            # Réinitialise si ce n'est plus en colère, ou si l'alerte est désactivée
            if emotion != "angry" or confidence <= conf_threshold or not APP_SETTINGS["alerts_enabled"]:
                self.angry_start_time = None
                self.is_alerting = False
                self.alert_triggered = False
            
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

def get_camera():
    global camera
    if camera is None: camera = cv2.VideoCapture(0)
    return camera

def generate_frames():
    global current_emotion
    model = load_model(EMOTION_MODEL)

    while True:
        cam = get_camera()
        success, frame = cam.read()
        if not success: break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # On injecte la sensibilité réglée par l'utilisateur
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
# FONCTIONS JSON
# ============================================
def load_reports():
    if os.path.exists(REPORTS_FILE):
        with open(REPORTS_FILE, 'r') as f: return json.load(f)
    return []

def save_report(report_data):
    reports = load_reports()
    reports.append(report_data)
    with open(REPORTS_FILE, 'w') as f: json.dump(reports, f, indent=4)

# ============================================
# ROUTES WEB
# ============================================
@app.route('/')
def index(): return render_template("Acceuil.html")
@app.route('/dashboard')
def dashboard(): return render_template("dashboard.html")
@app.route('/reports')
def reports(): return render_template("reports.html")
@app.route('/settings')
def settings(): return render_template("settings.html")
@app.route('/video_feed')
def video_feed(): return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ============================================
# API (Stats, Reports & Settings)
# ============================================
@app.route('/api/stats')
def api_stats():
    return jsonify({
        "total_customers": stats.get_display_customers(),
        "emotions": stats.get_stats(),
        "satisfaction_score": stats.get_satisfaction_score(),
        "current_emotion": current_emotion
    })

@app.route('/api/reset_stats', methods=['POST'])
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
def api_report():
    reports = load_reports()
    if not reports: return jsonify({"weekly_trend": [], "daily_data": []})
    recent = reports[-7:] if len(reports) > 7 else reports
    return jsonify({
        "weekly_trend": [{"day": r["date"].split(" ")[1], "satisfaction": r["satisfaction"]} for r in recent],
        "daily_data": list(reversed(reports))
    })

# --- NOUVELLES ROUTES POUR LES SETTINGS ---
@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify(APP_SETTINGS)

@app.route('/api/settings', methods=['POST'])
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