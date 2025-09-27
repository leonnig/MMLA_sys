from ultralytics import YOLO
import cv2
import behavior_analysis

model = YOLO('yolo11n.pt')

cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

frame_count = 0
frame_skip = 3
previous_results = None

LEARNING_OBJECTS = ["keyboard", "mouse", "board", "sensor"]  
HAND_OBJECTS = ["person"]  

def is_collision(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    return xA < xB and yA < yB

def image_detection():
    global frame_count
    global previous_results

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        # every frame_skip frames do prediction
        if frame_count % frame_skip == 0:
            # predict return results list; we only process the first result
            results = model.predict(frame, imgsz=640, conf=0.25, verbose=False)[0]
            previous_results = results
        
        hand_contact_status = "Idle" # 預設為未接觸

        learning = False
        if previous_results is not None:
            boxes = previous_results.boxes.xyxy.cpu().numpy()  # [x1, y1, x2, y2]
            classes = previous_results.boxes.cls.cpu().numpy()
            confidences = previous_results.boxes.conf.cpu().numpy()
            names = [model.model.names[int(c)] for c in classes]

            hands = []
            targets = []

            for i, name in enumerate(names):
                if name in HAND_OBJECTS:
                    hands.append((boxes[i], confidences[i], name))
                elif name in LEARNING_OBJECTS:
                    targets.append((boxes[i], confidences[i], name))

        
            for hand_box, hand_conf, hand_name in hands:
                for target_box, target_conf, target_name in targets:
                    if is_collision(hand_box, target_box):
                        hand_contact_status = target_name # 更新接觸狀態為物件名稱
                        break
                        learning = True
                        break
                if hand_contact_status != "Idle":
                    break
                if learning:
                    break

             # *** 核心修改：更新中央狀態 ***
            behavior_analysis.update_state("hand_contact", hand_contact_status)
            
            # Draw bounding boxes and labels
            for i, (box, conf, name) in enumerate([(boxes[i], confidences[i], names[i]) for i in range(len(names))]):
                x1, y1, x2, y2 = map(int, box)
                color = (0, 255, 0) if name in HAND_OBJECTS else (255, 0, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                label = f"{name} {conf:.2f}"
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        status_text = "Learning" if learning else "Idle"
        cv2.putText(frame, f"Status: {status_text}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 255, 0) if learning else (0, 0, 255), 2)

        cv2.imshow("YOLO11n Collision Learning", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()