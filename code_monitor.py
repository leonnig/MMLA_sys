import time
import threading
import tkinter as tk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from google import genai
import behavior_analysis
import os

API_KEY = 'AIzaSyAspel8yu6OK7CX07uzZp2qliS1ygxrFOY'
client = genai.Client(api_key=API_KEY)

CURRENT_WATCHING_FILE = None 

last_processed_time = 0
COOLDOWN_SECONDS = 15

def show_custom_messagebox(title, message):
    """ 在獨立執行緒中顯示 Tkinter 彈窗 """
    try:
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
        tk.Button(popup, text="我知道了", command=lambda: [popup.destroy(), root.destroy()], bg="#dddddd").pack(pady=5)

        # 設定 20 秒後自動關閉，避免學生不關視窗堆積
        root.after(20000, lambda: [popup.destroy(), root.destroy()])        
        root.mainloop()
    except Exception as e:
        print(f"[UI Error] 彈窗顯示失敗: {e}")

def trigger_ai_feedback(reason="stuck"):
    """
    這是一個公開函式，供 behavior_analysis 呼叫
    :param reason: 觸發原因，例如 "stuck" (卡住), "save" (存檔)
    """
    global CURRENT_WATCHING_FILE

    # Arduino 存檔時會先刪除舊檔再寫新檔，如果不等待，
    # Python 會在檔案「消失」的那一瞬間去讀取，導致 FileNotFound。
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
    
    print(f"[Code Monitor] 觸發 AI 反饋，原因：{reason}")

    t = threading.Thread(target=_perform_analysis, args=(CURRENT_WATCHING_FILE, reason))
    t.daemon = True
    t.start()

def _perform_analysis(filepath, reason):
    """ 實際執行讀檔與 API 呼叫的內部函式 """
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
    
    if reason == "stuck":
        context_prompt = """
                        你現在是一位蘇格拉底式的程式導師。學生似乎卡住了。
                        請不要直接寫出正確程式碼。
                        請觀察學生的程式碼邏輯，用 1 個問題引導他發現自己的盲點。
                        """
    else:
        context_prompt = """"
                        學生剛存檔。請快速檢查是否有明顯語法錯誤（如漏掉分號、括號不對稱）。
                        如果沒有錯誤，請給予簡短肯定。
                        如果有錯誤，請指出錯誤行數的大概位置，並簡單說明問題所在。
                        """

    prompt = f"""
    你是一個 Arduino 程式碼助教。
    情境：{context_prompt}
    
    --- 學生程式碼 ---
    {code_content}
    
    限制：80字以內，繁體中文，語氣溫柔，給多點情緒價值 。
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=[prompt]
        )
        advice = response.text
        print(f"[Gemini Advice ({reason})] {advice}")

        ui_thread = threading.Thread(target=show_custom_messagebox, 
                                     args=("AI 程式小助教", advice))
        ui_thread.daemon = True
        ui_thread.start()

    except Exception as e:
        print(f"[Gemini Error] {e}")


def analyze_code_with_gemini(filepath):
    """ 讀取程式碼並呼叫 Gemini """
    print(f"[Code Monitor] 偵測到變動：{filepath}")
    
    # 1. 更新 MMLA 狀態：學生正在寫程式
    behavior_analysis.update_state("last_code_save_time", time.time())
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code_content = f.read()

        prompt = f"""
        你是一個 Arduino 程式碼助教，協助國高中學生。
        請針對以下程式碼提供簡短的修正建議或鼓勵。
        注意要仔細檢查程式碼中的錯誤或潛在問題，包括語法錯誤要特別注意。
        限制：盡量不要超過 8 句，語氣親切，指出關鍵錯誤或給予肯定。
        
        --- 學生程式碼 ---
        {code_content}
        """
            
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=[prompt]
        )
        
        advice = response.text
        print(f"[Gemini Advice] {advice}")

        # 2. 顯示彈窗 (使用獨立線程避免卡住監控)
        ui_thread = threading.Thread(target=show_custom_messagebox, 
                                     args=("AI 程式小助教", advice))
        ui_thread.daemon = True
        ui_thread.start()

    except Exception as e:
        print(f"[Code Monitor Error] 分析失敗: {e}")

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

def start_monitoring(path_to_watch):
    global CURRENT_WATCHING_FILE

    all_ino_files = []
    for root, dirs, files in os.walk(path_to_watch):
        for file in files:
            if file.endswith(".ino"):
                full_path = os.path.join(root, file)
                all_ino_files.append(full_path)
    if all_ino_files:
        CURRENT_WATCHING_FILE = max(all_ino_files, key=os.path.getmtime) # 取最新修改的 .ino 檔案
        print(f"[Code Monitor] 啟動監控, 目標路徑: {path_to_watch})")
        print(f"[Cpde Monitor] 目前監控的 Arduino 檔案: {CURRENT_WATCHING_FILE}")
    else:
        print(f"[Code Monitor] 警告：在目標路徑中找不到任何 .ino 檔案: {path_to_watch}")
        return

    event_handler = ArduinoHandler()
    observer = Observer()
    observer.schedule(event_handler, path_to_watch, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()