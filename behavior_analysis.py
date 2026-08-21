#This is an analysis module，to catch every module's data and do some analysis
#For example, if eye gaze is "Left" and speech contains "困難", then we can say the user is having difficulty in looking left

import time
import requests
from collections import deque
import collections
from datetime import datetime
import csv
from google.cloud import storage
import os
from plyer import notification

# 新增系統暫停旗標
SYSTEM_PAUSED = False

# 控制是否顯示 OpenCV 畫面的開關 (預設為不顯示，節省效能)
SHOW_VIDEO = False

# 新增全域變數，供 UI 讀取當前狀態
current_behavior = "待命中"

# 維護學習者當前的多模態即時狀態
current_state = {
    "gaze": "Center",           # 初始值: "Left", "Center", "Right"
    "hand_contact": "Idle",     # 初始值: "keyboard", "mouse", "board", "Idle"
    "speech_keyword": None,     # 偵測到的關鍵字
    "speech_intent": "Silence",      # 偵測到的語音意圖類型
    "keyboard_active": False,   # 鍵盤是否在活動中
    "mouse_position": (0, 0),   # 滑鼠最後的位置
    "last_keyboard_time": time.time(), # 最後一次鍵盤活動時間
    "last_mouse_move_time": time.time(), # 最後一次滑鼠移動時間
    "last_code_save_time": 0,  # 最後一次程式碼儲存時間 
    "ai_feedback_active": False  # 記錄彈窗是否開啟
}

# define different feedback types and their cooldowns
feedbacks_rules = {
    "Passive: Off-task": {
        "message": "看起來有點分心囉，休息一下，然後我們繼續努力吧！，有不會的都可以直接問老師喔",
        "cooldown": 120, # 兩分鐘內不再提醒
        "persistence": 15 # 需要持續 15 秒才觸發
    },
    "Active: Writing Code": {
        "message": "持續編寫程式碼，很棒的投入！繼續保持！",
        "cooldown": 300, # 五分鐘內不再鼓勵
        "persistence": 0
    },
    "Interactive: Asking for help": {
        "message": "提出問題是進步的關鍵，做得很好！",
        "cooldown": 180, # 三分鐘內不再提醒
        "persistence": 0
    }  
}


behaviour_log = deque(maxlen=600) # 只保留最近600筆
ANALYSIS_INTERVAL = 60  # 1 min
last_analysis_time = time.time()

# 用於判斷是否長時間無活動的閾值 (秒)
INACTIVE_THRESHOLD = 5 
OFF_TASK_THRESHOLD = 10 # 超過10秒無任何互動才算脫離任務

feedback_state = {
    "off_task_start_time": None, # 記錄脫離任務開始的時間
    "last_feedback_time": {},    # 記錄各類反饋的最後發送時間，避免頻繁打擾
}

# last_behavior_state = "Unknown"
# behavior_state_time = time.time()

# 定義觸發 AI 介入的閾值 (秒)
STUCK_THRESHOLD = 15 # if Viewing Code in 60s
AI_COOLDOWN = 20    # AI cooldown time 

last_ai_trigger_time = 0
last_active_writing_trigger = 0
last_active_exp_trigger = 0
ACTIVE_AI_COOLDOWN = 180

# 用於「平滑化」追蹤卡關狀態的計時器
stuck_start_time = None  
noise_start_time = None  
TOLERANCE_SECONDS = 3.0  # 容忍 3 秒的視線飄移或誤判 (雜訊)

# 新手保護盾變數
grace_period_end_time = 0

def reset_grace_period(seconds=60):
    """ 啟動新手保護盾，指定秒數內不觸發卡關反饋 """
    global grace_period_end_time, stuck_start_time, noise_start_time
    grace_period_end_time = time.time() + seconds
    # 同時清空之前的卡關計時，確保重新計算
    stuck_start_time = None
    noise_start_time = None
    print(f"\n[Behavior Analysis] 🛡️ 啟動新手保護期！ {seconds} 秒內暫停主動卡關偵測。")

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
        # 更新對應的活動時間戳F
        if source == "speech_intent" and value != "Silence":
            print(f"[State Update] 語音狀態更新: {value}")
        if source == "keyboard_active" and value:
            current_state["last_keyboard_time"] = time.time()
        elif source == "mouse_position":
            current_state["last_mouse_move_time"] = time.time()
        elif source == "gaze" or source == "hand_contact":
            # 視線或手部接觸變化也算是活動
            current_state["last_mouse_move_time"] = time.time()
        elif source == "speech_intent" and value != "Silence":
            current_state["last_mouse_move_time"] = time.time()

def upload_log_to_gcs(log_data, bucket_name, student_id):
    """ 將行為紀錄儲存為 CSV 並上傳到 Google Cloud Storage """
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_filename = f"behavior_log_{timestamp_str}.csv"

    formatted_log = []
    for timestamp, behavior in log_data:
        human_readable_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        formatted_log.append((human_readable_time, behavior))

    try:
        with open(local_filename, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Timestamp", "Behavior"])
            writer.writerows(formatted_log)
    except Exception as e:
        print(f"[Data Saving] Error saving log to CSV: {e}")
        return
    
    #  設定 GCS 客戶端並上傳
    try:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'gcp-credentials.json'  # 請確保憑證檔案路徑正確

        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        destination_blob_name = f"logs/{student_id}/behavior_log_{timestamp_str}.csv"
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_filename(local_filename)
        print(f"\n[GCS Upload] 成功將 {local_filename} 上傳至 gs://{bucket_name}/{destination_blob_name}")
    
    except FileNotFoundError:
        print(f"\n[GCS Upload] 錯誤：找不到金鑰檔案 'gcp-credentials.json'。請確認檔案位置是否正確。")
    except Exception as e:
        print(f"\n[GCS Upload] 上傳至 GCS 時發生錯誤: {e}")

    finally: 
        if os.path.exists(local_filename):
            os.remove(local_filename)
            
def analyze_and_send_behavior():
    import code_monitor
    """
    根據 current_state 分析學習行為
    """
    global last_analysis_time, last_behavior_state, behavior_state_time, last_ai_trigger_time
    global stuck_start_time, noise_start_time
    global current_behavior
    
    global last_active_writing_trigger, last_active_exp_trigger, ACTIVE_AI_COOLDOWN
    
    while True:
        time.sleep(2) # 每 2 秒分析一次當前狀態

        # 🟢 新增：如果系統暫停，就不做任何行為判定與計時
        if SYSTEM_PAUSED:
            current_behavior = "系統暫停中"
            continue

        now = time.time()
        state = current_state
        behavior = "Unknown" # defined default behavior
        just_saved_code = (now - state["last_code_save_time"] < 10) # 定義 10 秒內有存檔，就算是在寫程式
        
        # --- ICAP 編碼規則判斷 ---

        # 判斷鍵盤是否仍在活動
        if now - state["last_keyboard_time"] > INACTIVE_THRESHOLD:
            if state["keyboard_active"]:
                update_state("keyboard_active", False)

        # 判斷是否脫離任務的邏輯 
        last_activity_time = max(state["last_keyboard_time"], state["last_mouse_move_time"])
        is_inactive_task = (now - last_activity_time > OFF_TASK_THRESHOLD and
                       state["hand_contact"] == "Idle")
        is_looking_away = state["gaze"] == "NoFace"
        is_off_task = is_inactive_task or is_looking_away

        speech_intent = state.get("speech_intent", "Silence")

        # 互動:請求協助
        if speech_intent == "Help_Seeking":
            behavior = "Interactive: Asking for help"
            # 處理完畢後重置，避免下一秒繼續計入
            update_state("speech_intent", "Silence") 
            update_state("speech_keyword", None)

        # 互動：同儕討論
        elif speech_intent == "Peer_Discussion":
            behavior = "Interactive: Peer Discussion"
            update_state("speech_intent", "Silence")
            update_state("speech_keyword", None)

        # 存檔並驗證結果 (建構) 
        elif just_saved_code and state["hand_contact"] in ["breadboard", "arduino"] and state["gaze"] == "NoFace":
            behavior = "Constructive: Testing & Debugging"

        # 撰寫程式碼 (主動)
        elif state["gaze"] in ["Left", "Center"] and (state["keyboard_active"] or just_saved_code):
            behavior = "Active: Writing Code"

        # 進行實驗 (主動)
        elif state["hand_contact"] in ["breadboard", "arduino"] and state["gaze"] == "NoFace":
            behavior = "Active: Experimenting"
            
        # 執行程式 (主動) - 此處需要更詳細的滑鼠位置定義
        # elif state["mouse_position"] in EXECUTION_AREA and is_click:
        #     behavior = "Active: Running Code"

        # 閱讀系統反饋 (被動)
        elif (state["gaze"] == "Left" or state["gaze"] == "Center") and not state["keyboard_active"] and state["ai_feedback_active"]:
            behavior = "Passive: Reading Feedback"

        # 查看程式碼 (被動)
        elif (state["gaze"] == "Right" or state["gaze"] == "Center") and not state["keyboard_active"] and not state["ai_feedback_active"]:
            behavior = "Passive: Viewing Code"

        # 脫離學習任務 (被動)
        elif is_off_task:
            behavior = "Passive: Off-task"

        current_behavior = behavior

        if behavior != "Unknown":
            behaviour_log.append((now, behavior))
            print(f"[Behavior Analysis] - Detected: {behavior} (Gaze: {state['gaze']}, Hand: {state['hand_contact']}, KB: {state['keyboard_active']})")

        # if behavior == last_behavior_state:
        #     duration = now - behavior_state_time
        # else:
        #     last_behavior_state = behavior
        #     behavior_state_time = now
        #     duration = 0

        target_behaviors = ["Passive: Viewing Code", "Passive: Off-task"]

        if behavior in target_behaviors:
            # 確實處於卡關/發呆狀態
            if stuck_start_time is None:
                stuck_start_time = now # 開始計時
            noise_start_time = None    # 清除雜訊計時
            duration = now - stuck_start_time
        else:
            # 處於非卡關狀態 (可能是在寫扣，也可能是轉頭的短暫 Unknown 雜訊)
            if stuck_start_time is not None:
                if noise_start_time is None:
                    noise_start_time = now # 雜訊開始計時
                
                # 檢查雜訊是否超過容忍時間 (3秒)
                if now - noise_start_time > TOLERANCE_SECONDS:
                    # 真的脫離卡關狀態了！重置所有計時器
                    stuck_start_time = None
                    noise_start_time = None
                    duration = 0
                else:
                    # 還在容忍時間內，假裝他還在卡關，繼續累計時間！
                    duration = now - stuck_start_time
            else:
                duration = 0   

        # --- 觸發 AI 介入 ---
        if duration > STUCK_THRESHOLD:
            if now < grace_period_end_time:
                # 仍在保護期內，安靜地跳過，不觸發 AI
                pass
            elif now - last_ai_trigger_time > AI_COOLDOWN:
                # 依當前狀態分流：脫離任務 -> 再投入提示；盯著程式碼不動 -> 卡關引導
                trigger_reason = "off_task" if behavior == "Passive: Off-task" else "stuck"
                print(f"\n[Behavior Trigger] 學生處於被動狀態已超過 {duration:.0f} 秒 (包含容錯)，判定為 {trigger_reason}。")
                print("[Behavior Trigger] 呼叫 code_monitor 啟動 AI 輔助...")
                try:
                    code_monitor.trigger_ai_feedback(reason=trigger_reason)
                    last_ai_trigger_time = now
                    # 觸發後重置計時器，準備下一輪判定
                    stuck_start_time = now 
                except Exception as e:
                    print(f"[Behavior Trigger] 呼叫 AI 輔助失敗: {e}")
        # 2. 處理主動撰寫程式碼 (新增邏輯)
        if behavior == "Active: Writing Code":
            if now - last_active_writing_trigger > ACTIVE_AI_COOLDOWN:
                try:
                    code_monitor.trigger_ai_feedback(reason="writing")
                    last_active_writing_trigger = now
                except Exception as e:
                    pass

        # 3. 處理進行硬體實驗 (新增邏輯)
        if behavior == "Active: Experimenting":
             if now - last_active_exp_trigger > ACTIVE_AI_COOLDOWN:
                try:
                    code_monitor.trigger_ai_feedback(reason="experimenting")
                    last_active_exp_trigger = now
                except Exception as e:
                    pass

        # --- 以下為定期印出最高頻率行為的邏輯 ---
        if now - last_analysis_time >= ANALYSIS_INTERVAL:
            window_start = now - ANALYSIS_INTERVAL
            recent_logs = [b for t, b in behaviour_log if t >= window_start]
            
            if recent_logs:
                counter = collections.Counter(recent_logs)
                most_common, freq = counter.most_common(1)[0]
                print(f"[Behavior Analysis] - In the past 1 minutes, the most frequent behavior was: {most_common} ({freq} times)")

                rule = feedbacks_rules.get(most_common)
                if rule:
                    try:
                        notification.notify(
                            title="MMLA 學習小提醒",
                            message=rule["message"],
                            timeout=10
                        )
                        feedback_state["last_feedback_time"][most_common] = now
                        feedback_state["off_task_start_time"] = None
                        print(f"[Feedback Sent] Notified user about: {most_common}")
                    except Exception as e:
                        print(f"[Feedback Error] Failed to send notification: {e}")

                else:
                    print("== 兩分鐘內無行為紀錄 ==")

                last_analysis_time = now

        # if behavior in target_behaviors and duration > STUCK_THRESHOLD:
        #     if now - last_ai_trigger_time > AI_COOLDOWN:
        #         print(f"\n[Behavior Trigger] 學生處於 {behavior} 已超過 {duration:.0f} 秒，判定為卡關或分心。")
        #         print("[Behavior Trigger] 呼叫 code_monitor 啟動 AI 輔助...")
        #         try:
        #             code_monitor.trigger_ai_feedback(reason="stuck")
        #             last_ai_trigger_time = now
        #         except Exception as e:
        #             print(f"[Behavior Trigger] 呼叫 AI 輔助失敗: {e}")        

        # if now - last_analysis_time >= ANALYSIS_INTERVAL:
        #     window_start = now - ANALYSIS_INTERVAL
        #     recent_logs = [b for t, b in behaviour_log if t >= window_start]
            
        #     if recent_logs:
        #         counter = collections.Counter(recent_logs)
        #         most_common, freq = counter.most_common(1)[0]
        #         print(f"[Behavior Analysis] - In the past 1 minutes, the most frequent behavior was: {most_common} ({freq} times)")
            
        #     else:
        #          print("== 兩分鐘內無行為紀錄 ==")
        #     last_analysis_time = now

        #     rule = feedbacks_rules.get(most_common)

        #     # --- 發送通知 ---
        #     try:
        #         notification.notify(
        #             title="MMLA 學習小提醒",
        #             message=rule["message"],
        #             timeout=10  # 通知顯示 10 秒
        #         )
        #         # 更新最後發送時間
        #         feedback_state["last_feedback_time"][behavior] = now
        #         # 重置 off-task 計時器，避免連續觸發
        #         feedback_state["off_task_start_time"] = None
        #         print(f"[Feedback Sent] Notified user about: {behavior}")
        #     except Exception as e:
        #         print(f"[Feedback Error] Failed to send notification: {e}")