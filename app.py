from flask import Flask, render_template, Response, jsonify
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
import cv2
import numpy as np
from collections import Counter, deque
from datetime import datetime
import time

app = Flask(__name__)

# ============================================
# CONFIGURATION
# ============================================
EMOTION_MODEL = "Emotion_little_vgg.h5"
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
EMOTIONS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']

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
        
        # Logique d'alerte : 10 secondes de colère
        if emotion == "angry" and confidence > 0.70:
            if self.angry_start_time is None:
                self.angry_start_time = time.time()
            elif time.time() - self.angry_start_time > 10:
                if not self.alert_triggered:
                    self.alert_triggered = True
                    return True
        else:
            self.angry_start_time = None
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
        # Détection équilibrée
        faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))

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
                current_emotion["alert"] = True # Déclenche l'alerte pour le front-end

            # Rendu visuel propre sur la caméra
            # On dessine en blanc pour le contraste, texte plus grand
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 255, 255), 2)
            cv2.putText(frame, f"{emotion.upper()}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# ============================================
# ROUTES
# ============================================
@app.route('/')
def index():
    # Route racine pointe vers la nouvelle Landing Page
    return render_template("Acceuil.html")

@app.route('/dashboard')
def dashboard(): 
    return render_template("dashboard.html")

@app.route('/reports')
def reports(): 
    return render_template("reports.html")

@app.route('/settings')
def settings(): 
    return render_template("settings.html")

@app.route('/video_feed')
def video_feed(): return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

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
    stats.reset()
    return jsonify({"status": "success"})

# Fausse API pour les rapports historiques
@app.route('/api/report')
def api_report():
    return jsonify({
        "total_customers": 150,
        "total_alerts": 6,
        "weekly_trend": [
            {"day":"Mon","satisfaction":80},
            {"day":"Tue","satisfaction":84},
            {"day":"Wed","satisfaction":78},
            {"day":"Thu","satisfaction":88},
            {"day":"Fri","satisfaction":82},
            {"day":"Sat","satisfaction":90},
            {"day":"Sun","satisfaction":92}
        ],
        "daily_data": [
            {"date":"2026-04-10", "satisfaction":78},
            {"date":"2026-04-11", "satisfaction":84},
            {"date":"2026-04-12", "satisfaction":90}
        ]
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)