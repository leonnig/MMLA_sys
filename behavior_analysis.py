#This is an analysis module，to catch every module's data and do some analysis
#For example, if eye gaze is "Left" and speech contains "困難", then we can say the user is having difficulty in looking left

import time
import requests
from collections import deque
import collections
from datetime import datetime
import csv

#SERVER_URL = "http://127.0.0.1:5000/api/behavior" # 假設這是接收行為分析結果的 API

# 維護學習者當前的多模態即時狀態
current_state = {
    "gaze": "Center",           # 初始值: "Left", "Center", "Right"
    "hand_contact": "Idle",     # 初始值: "keyboard", "mouse", "board", "Idle"
    "speech_keyword": None,     # 偵測到的關鍵字
    "keyboard_active": False,   # 鍵盤是否在活動中
    "mouse_position": (0, 0),   # 滑鼠最後的位置
    "last_keyboard_time": time.time(), # 最後一次鍵盤活動時間
    "last_mouse_move_time": time.time(), # 最後一次滑鼠移動時間
}

behaviour_log = [] # [()(timestamp, behavior)]
behaviour_log = deque(maxlen=600) # 只保留最近600筆
ANALYSIS_INTERVAL = 60  # 2 min
last_analysis_time = time.time()

# 用於判斷是否長時間無活動的閾值 (秒)
INACTIVE_THRESHOLD = 5 
OFF_TASK_THRESHOLD = 10 # 超過10秒無任何互動才算脫離任務

# --- 狀態更新函式 ---
def update_state(source, value):
    """
    供各個感測器模組呼叫的統一狀態更新函式
    :param source: 數據來源模組，例如 "gaze", "hand_contact"
    :param value: 該模組傳來的數據
    """
    global current_state
    if source in current_state:
        current_state[source] = value
        # 更新對應的活動時間戳
        if source == "keyboard_active" and value:
            current_state["last_keyboard_time"] = time.time()
        elif source == "mouse_position":
            current_state["last_mouse_move_time"] = time.time()
        elif source == "gaze" or source == "hand_contact":
            # 視線或手部接觸變化也算是活動
            current_state["last_mouse_move_time"] = time.time()

# save file function
def save_log_to_csv(log_data):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"behavior_log_{timestamp}.csv"

    print(f"\n[Data Saving] Saving behavior log to {filename}...")

    try: 
        # list to sa save transformatted list
        formatted_log = []

        for timestamp, behavior in log_data:
            time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            formatted_log.append((time_str, behavior))

        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Behavior"])
            writer.writerows(formatted_log)
            
        print(f"[Data Saving] Successfully saved {len(log_data)} records to {filename}.")
    except Exception as e:
        print(f"[Data Saving] Error saving log to CSV: {e}")

def analyze_and_send_behavior():
    """
    根據 current_state 分析學習行為，並將結果傳送到伺服器
    """
    global last_analysis_time

    while True:
        time.sleep(2) # 每 2 秒分析一次當前狀態
        now = time.time()
        state = current_state
        behavior = "Unknown" # 預設行為
        
        # --- ICAP 編碼規則判斷 ---

        # 判斷鍵盤是否仍在活動
        if time.time() - state["last_keyboard_time"] > INACTIVE_THRESHOLD:
            if state["keyboard_active"]:
                update_state("keyboard_active", False)

        # *** 核心修正：判斷是否脫離任務的邏輯 ***
        last_activity_time = max(state["last_keyboard_time"], state["last_mouse_move_time"])
        is_inactive_task = (time.time() - last_activity_time > OFF_TASK_THRESHOLD and
                       state["hand_contact"] == "Idle")
        is_looking_away = state["gaze"] == "NoFace"
        is_off_task = is_inactive_task or is_looking_away

        # 請求協助 (互動)
        if state["speech_keyword"] in ["老師", "請問", "好難"]:
            behavior = "Interactive: Asking for help"
            # 將其視為一次性事件，處理完畢後立刻將關鍵字狀態重設為 None
            update_state("speech_keyword", None)

        # 撰寫程式碼 (主動)
        elif state["gaze"] in ["Left", "Center"] and state["keyboard_active"]:
            behavior = "Active: Writing Code"

        # 進行實驗 (主動)
        elif state["hand_contact"] in ["board", "sensor", "mouse", "keyboard"]:
            behavior = "Active: Experimenting"
            
        # 執行程式 (主動) - 此處需要更詳細的滑鼠位置定義
        # elif state["mouse_position"] in EXECUTION_AREA and is_click:
        #     behavior = "Active: Running Code"

        # 查看程式碼 (被動)
        elif (state["gaze"] == "Right" or state["gaze"] == "Center") and not state["keyboard_active"]:
            behavior = "Passive: Viewing Code"

        # 閱讀系統反饋 (被動)
        elif state["gaze"] == "Left" and not state["keyboard_active"]:
            behavior = "Passive: Reading Feedback"

        # 脫離學習任務 (被動)
        elif is_off_task:
            behavior = "Passive: Off-task"
    
    
        
        # 其他更複雜的規則可以在此擴充...

        if behavior != "Unknown":
            behaviour_log.append((now, behavior))
            print(f"[Behavior Analysis] - Detected: {behavior} (Gaze: {state['gaze']}, Hand: {state['hand_contact']}, KB: {state['keyboard_active']})")
            
            # # (可選) 將分析結果傳送到伺服器
            # try:
            #     requests.post(SERVER_URL, json={"behavior": behavior, "timestamp": time.time()})
            # except requests.exceptions.RequestException as e:
            #     print(f"Error sending behavior data: {e}")

        if now - last_analysis_time >= ANALYSIS_INTERVAL:
            window_start = now - ANALYSIS_INTERVAL
            past_two_min = [b for t, b in behaviour_log if t >= window_start]
            if past_two_min:
                counter = collections.Counter(past_two_min)
                most_common, freq = counter.most_common(1)[0]
                print(f"[Behavior Analysis] - In the past 2 minutes, the most frequent behavior was: {most_common} ({freq} times)")
            else:
                 print("== 兩分鐘內無行為紀錄 ==")
            last_analysis_time = now
