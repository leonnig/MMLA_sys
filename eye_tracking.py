import cv2
import mediapipe as mp
import time
import requests
import behavior_analysis

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

def calculate_iris_center(face_landmarks, w, h, iris_points):
    xs = [face_landmarks.landmark[p].x * w for p in iris_points]
    ys = [face_landmarks.landmark[p].y * h for p in iris_points]
    center_x = sum(xs) / len(xs)
    center_y = sum(ys) / len(ys)
    return center_x, center_y

def eye_gaze_tracking():

    LEFT_IRIS_POINTS = [468, 469, 470, 471, 472]
    RIGHT_IRIS_POINTS = [473, 474, 475, 476, 477, 478, 479]  # 如果需要也可用右眼
    
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

        # default state is "NoFace"
        gaze = "NoFace"
        
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

                # draw iris points for left eye
                for idx in LEFT_IRIS_POINTS + [LEFT_EYE_LEFT_CORNER, LEFT_EYE_RIGHT_CORNER]:
                    cx = int(face_landmarks.landmark[idx].x * w)
                    cy = int(face_landmarks.landmark[idx].y * h)
                    cv2.circle(image, (cx, cy), 3, (0, 0, 255), -1)
                
                # calculate iris center with multiple points
                left_iris_center_x, _ = calculate_iris_center(face_landmarks, w, h, LEFT_IRIS_POINTS)
                left_eye_left_x = face_landmarks.landmark[LEFT_EYE_LEFT_CORNER].x * w
                left_eye_right_x = face_landmarks.landmark[LEFT_EYE_RIGHT_CORNER].x * w

                eye_width = left_eye_right_x - left_eye_left_x
                if eye_width != 0:
                    iris_offset = left_iris_center_x - left_eye_left_x
                    ratio = iris_offset / eye_width
                    if ratio < 0.43:
                        gaze = "Left"
                    elif ratio > 0.57:
                        gaze = "Right"
                    else:
                        gaze = "Center"
        behavior_analysis.update_state("gaze", gaze)

        end = time.time()
        fps = 1 / (end - start) if (end - start) != 0 else 0


        cv2.putText(image, f"Gaze: {gaze}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.putText(image, f"FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

        cv2.imshow('Gaze tracking (mediapipe)', image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()