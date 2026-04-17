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
EMOTION_MODEL = "Emotion_restaurant.h5"

FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

EMOTIONS = ['angry', 'happy', 'neutral', 'sad', 'surprise']

EMOTION_ICONS = {
    'angry': '',
    'happy': '',
    'neutral': '',
    'sad': '',
    'surprise': ''
}

EMOTION_COLORS = {
    'angry': '#dc3545',
    'happy': '#28a745',
    'neutral': '#17a2b8',
    'sad': '#6c757d',
    'surprise': '#fd7e14'
}

# ============================================
# STATS CLASS
# ============================================
class EmotionStats:
    def __init__(self):
        self.reset()

    def reset(self):
        self.total_faces = 0
        self.emotion_counts = Counter()
        self.emotion_timeline = deque(maxlen=100)
        self.angry_start_time = None
        self.alert_triggered = False

    def add_detection(self, emotion, confidence):
        self.total_faces += 1
        self.emotion_counts[emotion] += 1

        self.emotion_timeline.append({
            "emotion": emotion,
            "confidence": float(confidence),
            "time": datetime.now().strftime("%H:%M:%S")
        })

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
        if self.total_faces == 0:
            return 0

        good = self.emotion_counts["happy"] + self.emotion_counts["neutral"]
        return int((good / self.total_faces) * 100)

    def get_stats(self):
        data = {}

        for emotion in EMOTIONS:
            count = self.emotion_counts[emotion]

            percentage = 0
            if self.total_faces > 0:
                percentage = round((count / self.total_faces) * 100, 1)

            data[emotion] = {
                "count": count,
                "percentage": percentage,
                "icon": EMOTION_ICONS[emotion],
                "color": EMOTION_COLORS[emotion]
            }

        return data


stats = EmotionStats()

# ============================================
# CAMERA
# ============================================
camera = None

current_emotion = {
    "emotion": "neutral",
    "confidence": 0,
    "face_detected": False
}


def get_camera():
    global camera

    if camera is None:
        camera = cv2.VideoCapture(0)

    return camera


# ============================================
# ALERT
# ============================================
def send_alert():
    print("ALERT: Angry customer detected > 10 sec")


# ============================================
# VIDEO STREAM
# ============================================
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
            scaleFactor=1.3,
            minNeighbors=5
        )

        current_emotion["face_detected"] = len(faces) > 0

        for (x, y, w, h) in faces:
            roi = gray[y:y+h, x:x+w]
            roi = cv2.resize(roi, (48, 48))

            roi = roi.astype("float") / 255.0
            roi = img_to_array(roi)
            roi = np.expand_dims(roi, axis=0)

            prediction = model.predict(roi, verbose=0)[0]

            print("Scores:", prediction)
            print("Predicted Index:", np.argmax(prediction))

             
            emotion_index = np.argmax(prediction)
            confidence = float(np.max(prediction))
            emotion = EMOTIONS[emotion_index]

              
            current_emotion["emotion"] = emotion
            current_emotion["confidence"] = confidence

            alert = stats.add_detection(emotion, confidence)

            if alert:
                send_alert()

            cv2.rectangle(
                frame,
                (x, y),
                (x+w, y+h),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"{emotion} {confidence:.2f}",
                (x, y-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            frame +
            b'\r\n'
        )


# ============================================
# ROUTES
# ============================================
@app.route('/')
def dashboard():
    return render_template("dashboard.html")


@app.route('/reports')
def reports():
    return render_template("reports.html")


@app.route('/settings')
def settings():
    return render_template("settings.html")


@app.route('/video_feed')
def video_feed():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/stats')
def api_stats():
    return jsonify({
        "total_faces": stats.total_faces,
        "emotions": stats.get_stats(),
        "satisfaction_score": stats.get_satisfaction_score(),
        "current_emotion": current_emotion
    })


@app.route('/api/reset_stats', methods=['POST'])
def reset_stats():
    stats.reset()
    return jsonify({"status": "success"})


@app.route('/api/timeline')
def api_timeline():
    return jsonify(list(stats.emotion_timeline))



@app.route('/api/report')
def api_report():

    return jsonify({
        "total_customers": 150,
        "satisfaction_rate": 82,
        "peak_negative_hour": "19:00",
        "total_alerts": 6,

        "emotion_distribution": {
            "happy": 55,
            "neutral": 22,
            "angry": 10,
            "sad": 8,
            "surprise": 5
        },

        "weekly_trend": [
            {"day":"Mon","satisfaction":80},
            {"day":"Tue","satisfaction":84},
            {"day":"Wed","satisfaction":78},
            {"day":"Thu","satisfaction":88},
            {"day":"Fri","satisfaction":82}
        ],

       'hourly_data': [
    {'hour': 12, 'angry': 3, 'sad': 2, 'happy': 15, 'value': 5},
    {'hour': 13, 'angry': 5, 'sad': 3, 'happy': 20, 'value': 8},
    {'hour': 14, 'angry': 8, 'sad': 4, 'happy': 18, 'value': 12},
    {'hour': 15, 'angry': 4, 'sad': 2, 'happy': 22, 'value': 6},
    {'hour': 16, 'angry': 2, 'sad': 1, 'happy': 25, 'value': 3},
    {'hour': 17, 'angry': 1, 'sad': 0, 'happy': 30, 'value': 1},
    {'hour': 18, 'angry': 6, 'sad': 3, 'happy': 20, 'value': 9},
    {'hour': 19, 'angry': 4, 'sad': 2, 'happy': 25, 'value': 6},
    {'hour': 20, 'angry': 2, 'sad': 1, 'happy': 28, 'value': 3}
],

        "daily_data": [
            {
                "date":"2026-04-10",
                "happy":50,
                "neutral":20,
                "angry":10,
                "sad":5,
                "surprise":3,
                "satisfaction":78
            }
        ]
    })

# ============================================
# RUN
# ============================================
if __name__ == '__main__':
    print("Restaurant Emotion Analytics")
    print("http://localhost:5000")

    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )