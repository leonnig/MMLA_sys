import time
import threading
import tkinter as tk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import openai
import behavior_analysis
import os
import datetime

API_KEY = ""
client = openai.OpenAI(api_key=API_KEY)

GLOBAL_LAST_CALL_TIME = 0       # 記錄上一次呼叫的時間
SAFE_INTERVAL = 180             # 設定冷卻時間 180 秒 (3分鐘)

CURRENT_WATCHING_FILE = None 

last_processed_time = 0
COOLDOWN_SECONDS = 15

AI_FEEDBACK_HISTORY = []  # 儲存歷史記憶的陣列
MAX_HISTORY_LENGTH = 3    # 只記憶最近 3 次，避免 Prompt 過長消耗 Token

def show_custom_messagebox(title, message):
    """ 在獨立執行緒中顯示 Tkinter 彈窗 """
    try:
        # 彈窗準備顯示，通知系統進入 AI Feedback 狀態
        behavior_analysis.update_state("ai_feedback_active", True)

        root = tk.Tk()
        root.withdraw()  # hide main window

        popup = tk.Toplevel(root)
        popup.title(title)
        popup.attributes('-topmost', True)  # topmost display

        # Calculate position (bottom right)
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        popup_width = 450
        popup_height = 200

        x_pos = int(screen_width * 0.7)
        y_pos = int(screen_height * 0.7)

        popup.geometry(f"{popup_width}x{popup_height}+{x_pos}+{y_pos}")
        tk.Label(popup, text = message, padx = 10, pady = 10,
                 justify = tk.LEFT, wraplength = popup_width - 20, bg = "#f0f0f0", 
                 font = ("Arial", 10)).pack(expand=True, fill='both')
        
        # 定義一個關閉視窗的處理函式
        def close_popup():
            # 彈窗關閉，通知系統解除 AI Feedback 狀態
            behavior_analysis.update_state("ai_feedback_active", False)
            popup.destroy()
            root.destroy()

        # 攔截右上角的「Ｘ」，強制導向 close_popup
        popup.protocol("WM_DELETE_WINDOW", close_popup)

        tk.Button(popup, text="我知道了", command=close_popup, bg="#dddddd").pack(pady=5)

        # 設定 10 秒後自動關閉，避免學生不關視窗堆積
        root.after(120000, close_popup)        
        root.mainloop()
    except Exception as e:
        print(f"[UI Error] 彈窗顯示失敗: {e}")
        # 發生錯誤時確保狀態不會卡在 True
        behavior_analysis.update_state("ai_feedback_active", False)

def trigger_ai_feedback(reason="stuck"):
    """
    這是一個公開函式，供 behavior_analysis 呼叫
    :param reason: 觸發原因，例如 "stuck" (卡住), "save" (存檔)
    """
    global CURRENT_WATCHING_FILE, GLOBAL_LAST_CALL_TIME, SAFE_INTERVAL 

    now = time.time()
    time_diff = now - GLOBAL_LAST_CALL_TIME
    # 如果距離上次呼叫還不到 5 分鐘，就直接擋掉！
    if time_diff < SAFE_INTERVAL:
        print(f"🛑 [API 守門員] 阻擋呼叫！還在冷卻中 (剩餘 {int(SAFE_INTERVAL - time_diff)} 秒)。原因: {reason}")
        return  # <--- 這裡直接結束，保護您的額度

    # Arduino 存檔時會先刪除舊檔再寫新檔，如果不等待，
    # Python 會在檔案「消失」的那一瞬間去讀取，導致 FileNotFound。
    if reason == "save":
        print("[Debug] 等待檔案寫入完成...")
        time.sleep(1.0) 

    target_file = CURRENT_WATCHING_FILE

    # 雙重檢查：確保變數有值
    if not target_file:
        print("[Code Monitor] ❌ 錯誤：尚未鎖定任何 .ino 檔案。")
        return

     # 三重檢查：確保檔案真的存在於硬碟上
    if not os.path.exists(target_file):
        print(f"[Code Monitor] ❌ 錯誤：檔案似乎消失了或無法讀取: {target_file}")
        # 再給一次機會 (有些人電腦比較慢)
        time.sleep(1.0)
        if not os.path.exists(target_file):
            return
    GLOBAL_LAST_CALL_TIME = now 
    print(f"[Code Monitor] 觸發 AI 反饋，原因：{reason}")

    t = threading.Thread(target=_perform_analysis, args=(CURRENT_WATCHING_FILE, reason))
    t.daemon = True
    t.start()

def _perform_analysis(filepath, reason):
    """ 實際執行讀檔與 API 呼叫的內部函式 """
    global AI_FEEDBACK_HISTORY  # 確保修改的是外面的全域記憶
    code_content = None 
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code_content = f.read()
            break  
        except PermissionError:
            time.sleep(0.5)
        except Exception:
            return
    if not code_content:
        return
    
    #讀取目前的語音狀態
    current_state = behavior_analysis.current_state
    speech_intent = current_state.get("speech_intent", "Silence")
    speech_kw = current_state.get("speech_keyword", "")

    if speech_intent == "Help_Seeking":
        context_prompt = f"""
        【緊急情境：學生口頭求救】
        學生剛喊出求救關鍵字：「{speech_kw}」，情緒可能焦慮。
        請先以溫柔、安撫的語氣回應，給予情緒價值。
        接著對照程式碼第一行標示的任務目標，找出學生當下最關鍵的錯誤或邏輯盲點，
        明確「指出問題所在的位置」，並給出「第一步可以怎麼嘗試」的具體方向。
        此時可給比平常更直接的提示，但仍不要直接寫出完整的修正後程式碼，保留讓學生自己動手改的空間
        """
        # 重要：使用完這次語音意圖後，建議將其重置，避免下次存檔又重複觸發
        behavior_analysis.update_state("speech_intent", "Silence")

    elif speech_intent == "Peer_Discussion":
        context_prompt = f"""
        【協作情境：同儕討論】
        學生正在與同學討論，關鍵字：「{speech_kw}」。同儕討論是高層次的協作學習，
        請以「不打斷、不搶話」為原則，扮演從旁點撥的協作引導者。
        請勿直接給答案或評斷對錯；改為依他們的程式碼，拋出一個簡短的「驗證性問題」或「思考實驗」，
        引導他們自行檢驗彼此的想法（例如：如果把這個值改成 X，你們覺得會發生什麼？）。
        語氣輕鬆、像同學插話一樣，讓學生可以選擇參考或忽略。
        """
        behavior_analysis.update_state("speech_intent", "Silence")
    
    elif reason == "stuck":
        context_prompt = """
                        【ICAP 被動情境：觀察程式碼】
                        你現在是一位蘇格拉底式的程式導師。學生似乎卡住了，一直觀察程式碼卻沒下手。
                        請觀察學生的目前的程式碼邏輯，找出他可能卡住的「邏輯盲點」
                        例如：迴圈條件設定、變數未初始化）。
                        提出具啟發性的封閉或開放式問題，引導他自己思考下一步，
                        可以提供程式碼給他提示或參考
                        """
    elif reason == "off_task":
        context_prompt = """
                        【情境：學生疑似分心 / 脫離任務】
                        系統偵測到學生已一段時間沒有任何操作、且視線離開螢幕，可能暫時分心，或已卡關到想放棄。
                        請以輕鬆、不帶責備的語氣，溫和地把學生的注意力拉回任務（例如：嘿，還順利嗎？要不要我們從剛剛那一步再看一次？）。
                        請對照程式碼第一行標示的任務目標，用一句話提醒他「現在可以做的下一個小動作」，降低重新投入的門檻。
                        不要長篇大論、也不要直接給程式碼或除錯，重點是重新喚起參與，而不是替他解題。
                        """
    elif reason == "writing":
        context_prompt = """
                        【主動情境：專注撰寫程式碼】
                        學生目前正專注地在鍵盤上敲擊，撰寫程式碼。請扮演一位默默在背後支持的助教。
                        任務限制：
                        1. 觀察他最新寫出的「具體程式碼片段」（例如特定的變數命名、迴圈結構、或腳位設定）。
                        2. 針對該片段給予一句簡短、具體的稱讚（例如：「看到你順利把 ledPin 設為 OUTPUT 了，架構很清晰！」）。
                        3. 絕對禁止：提出任何問題、給予任何除錯建議。
                        輸出風格：充滿能量的短句，字數控制在 50 字以內，純粹提供情緒價值與正向增強。
                        """
    elif reason == "experimenting":
        context_prompt = """
                        【主動情境：硬體接線與實驗測試】
                        學生目前視線離開螢幕，正在動手處理 Arduino 與麵包板的實體接線。請扮演一位實作經驗豐富的硬體助教。
                        請根據他目前程式碼中宣告的硬體元件，提供一個溫馨的「硬體防呆小提醒」（例如檢查腳位、正負極或 GND），以及提醒他這個任務中的元件需要注意甚麼。
                        注意：語氣要像朋友般提醒，不要長篇大論。
                        """
    else:
        context_prompt = """"
                        【ICAP 建構情境：驗證任務成果】
                        學生剛存檔，代表學生會要進行驗證任務的階段。學生已經完成階段性的任務，不管有無錯誤，請先給予鼓勵。
                        再來請快速檢查是否有明顯語法錯誤（如漏掉分號、括號不對稱），以及有無程式邏輯錯誤。
                        每個程式碼第一行會標示此次任務的目標與條件，請務必去對照學生的 code 有無完成條件
                        如果沒有錯誤，請給予簡短肯定。
                        如果有錯誤，請指出錯誤並說明問題所在，盡量用提示的方式。
                        """
                        
    # 🧠 提取歷史記憶
    if AI_FEEDBACK_HISTORY:
        history_text = "\n".join(AI_FEEDBACK_HISTORY)
    else:
        history_text = "無過去紀錄，這是第一次指導。"

    # 將 Prompt 拆分為 System 與 User 角色
    messages = [
        {
            "role": "system", 
            "content": f"""你是一個 Arduino 程式碼助教，負責幫助國高中生完成任務，程式碼中都會有要學生填空的地方，請特別注意。
            情境：{context_prompt}

            [系統記憶 : 你過去幾次給這個學生的引導紀錄] :
            {history_text}

            請根據上面的記憶與當前程式碼進行判斷。如果學生一直在同一個地方卡關，或是沒有改掉你上次指出的錯誤，請改變引導策略，絕對不要重複一模一樣的建議。
            80字以內，繁體中文，語氣溫柔，給多點情緒價值。"""
        },
        {
            "role": "user", 
            "content": f"--- 學生程式碼 ---\n{code_content}"
        }
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-5.4", 
            messages=messages,
            temperature=0.7
        )
        advice = response.choices[0].message.content
        print(f"[GPT Advice ({reason})] {advice}")
        
        # 將這次的結果存入記憶中
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        memory_entry = f"[{current_time} 狀態:{reason}] 你的建議：{advice}"
        AI_FEEDBACK_HISTORY.append(memory_entry)

        # 維持記憶長度，超過就刪除最舊的
        if len(AI_FEEDBACK_HISTORY) > MAX_HISTORY_LENGTH:
            AI_FEEDBACK_HISTORY.pop(0)

        ui_thread = threading.Thread(target=show_custom_messagebox, 
                                     args=("AI 程式小助教", advice))
        ui_thread.daemon = True
        ui_thread.start()

    except Exception as e:
        print(f"[GPT Error] {e}")

class ArduinoHandler(FileSystemEventHandler):
    def on_modified(self, event):
        global last_processed_time, CURRENT_WATCHING_FILE, COOLDOWN_SECONDS
        if not event.is_directory and event.src_path.endswith(".ino"):
            now = time.time()
            # 如果距離上次處理不到 15 秒 (COOLDOWN_SECONDS)，就忽略這次存檔
            if now - last_processed_time < COOLDOWN_SECONDS:
                return
            detected_path = os.path.abspath(os.path.normpath(event.src_path))
            print(f"[Code Monitor] 偵測到存檔 (子資料夾): {detected_path}")

            CURRENT_WATCHING_FILE = detected_path 
            behavior_analysis.update_state("last_code_save_time", now)
            print(f"[File Saved] update file save time")
            trigger_ai_feedback(reason="save")
            last_processed_time = now

# 🟢 新增：宣告全域的 watchdog 變數，方便我們隨時隨地操控它
_observer = None
_watch = None
_event_handler = None

def set_monitoring_path(new_path):
    """ 動態切換監控路徑與最新檔案的公開函式 """
    global _observer, _watch, _event_handler, CURRENT_WATCHING_FILE
    
    # 重新掃描新資料夾，尋找最新的 .ino 檔
    all_ino_files = []
    for root, dirs, files in os.walk(new_path):
        for file in files:
            if file.endswith(".ino"):
                all_ino_files.append(os.path.join(root, file))
                
    if all_ino_files:
        CURRENT_WATCHING_FILE = max(all_ino_files, key=os.path.getmtime)
        print(f"[Code Monitor] 🔄 成功切換監控路徑: {new_path}")
        print(f"[Code Monitor] 🎯 鎖定最新檔案: {CURRENT_WATCHING_FILE}")
    else:
        CURRENT_WATCHING_FILE = None
        print(f"[Code Monitor] ⚠️ 警告：在新路徑中找不到任何 .ino 檔案: {new_path}")

    # 如果 watchdog 已經在跑，解除舊任務，綁定新任務！
    if _observer is not None:
        if _watch is not None:
            _observer.unschedule(_watch) # 放棄舊資料夾
        # 綁定新資料夾
        _watch = _observer.schedule(_event_handler, new_path, recursive=True)

def start_monitoring(path_to_watch):
    global _observer, _event_handler

    _observer = Observer()
    _event_handler = ArduinoHandler()

    # 呼叫我們剛剛寫的換軌函式，進行初次設定
    set_monitoring_path(path_to_watch)
    _observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _observer.stop()
    _observer.join()