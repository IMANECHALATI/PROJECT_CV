import cv2
import os

input_folder = "restaurant_Emotion_videos"
output_folder = "restaurant_dataset"

fps_extract = 2   # 2 images chaque seconde

for emotion in os.listdir(input_folder):

    emotion_path = os.path.join(input_folder, emotion)

    if not os.path.isdir(emotion_path):
        continue

    save_path = os.path.join(output_folder, emotion)
    os.makedirs(save_path, exist_ok=True)

    for video_name in os.listdir(emotion_path):

        video_path = os.path.join(emotion_path, video_name)

        cap = cv2.VideoCapture(video_path)

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps / fps_extract)

        count = 0
        saved = 0

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            if count % frame_interval == 0:

                filename = f"{video_name}_{saved}.jpg"

                cv2.imwrite(
                    os.path.join(save_path, filename),
                    frame
                )

                saved += 1

            count += 1

        cap.release()

print("Frames extracted successfully!")