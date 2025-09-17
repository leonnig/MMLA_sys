import cv2
import mediapipe as mp
import time
import requests

SERVER_URL = "http://127.0.0.1:5000/api/upload"  

def send_gaze_data(gaze, fps):
    data = {
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "gaze": gaze,
        "fps": fps
    }
    try:
        requests.post(SERVER_URL, json=data, timeout=1)
    except Exception as e:
        print(f"送出偵測資料失敗: {e}")

# initialize mediapipe face mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# eye skin landmark indexes
LEFT_EYE = list(range(474, 478))
RIGHT_EYE = list(range(469, 473))

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

LEFT_IRIS = 468
RIGHT_IRIS = 473

LEFT_EYE_LEFT_CORNER = 33
LEFT_EYE_RIGHT_CORNER = 133

RIGHT_EYE_LEFT_CORNER = 362
RIGHT_EYE_RIGHT_CORNER = 263

def eye_gaze_tracking():
    last_send = 0 #record last send time
    N = 2 # set send interval

    while cap.isOpened():
        success, image = cap.read()
        
        if not success:
            print("Detect eye failed. Please check your camera.")
            break

        start = time.time()

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        h, w, _ = image.shape
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                # draw face
                mp_drawing.draw_landmarks(
                    image=image,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style())

                # draw eyes
                for idx in LEFT_EYE + RIGHT_EYE:
                    x = int(face_landmarks.landmark[idx].x * w)
                    y = int(face_landmarks.landmark[idx].y * h)
                    cv2.circle(image, (x, y), 2, (0, 255, 0), -1)

                for idx in [LEFT_IRIS, LEFT_EYE_LEFT_CORNER, LEFT_EYE_RIGHT_CORNER]:
                    cx = int(face_landmarks.landmark[idx].x * w)
                    cy = int(face_landmarks.landmark[idx].y * h)
                    cv2.circle(image, (cx, cy), 3, (0, 0, 255), -1)  # red point for iris and eye corners

            
                left_iris_x = face_landmarks.landmark[468].x * w
                left_eye_left_x = face_landmarks.landmark[33].x * w
                left_eye_right_x = face_landmarks.landmark[133].x * w

                eye_width = left_eye_right_x - left_eye_left_x
                iris_offset = left_iris_x - left_eye_left_x

                # rate the gaze direction
                ratio = iris_offset / eye_width  

                if ratio < 0.35:
                    gaze = "Left"
                elif ratio > 0.65:
                    gaze = "Right"
                else:
                    gaze = "Center"

                # show
                cv2.putText(image, f"Gaze: {gaze}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        end = time.time()
        if end - start != 0:
            fps = 1 / (end - start)
        else:
            fps = 0

        now = time.time()
        if now - last_send >= N:
            send_gaze_data(gaze, 1)
            last_send = now
 
        cv2.putText(image, f"FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

        cv2.imshow('Gaze tracking (mediapipe)', image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
