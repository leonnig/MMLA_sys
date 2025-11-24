import time
import threading
import tkinter as tk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from google import genai
import behavior_analysis

API_KEY = 'AIzaSyAspel8yu6OK7CX07uzZp2qliS1ygxrFOY'
client = genai.Client(api_key=API_KEY)

last_processed_time = 0
COOLDOWN_SECONDS = 15

def show_custom_messagebox(title, message):
    """ 在獨立執行緒中顯示 Tkinter 彈窗 """
    try:
        root = tk.Tk()
        root.withdraw()  # 隱藏主視窗

        popup = tk.Toplevel(root)
        popup.title(title)
        popup.attributes('-topmost', True)  # 置頂顯示

        # 計算位置 (右下角)
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
        限制：最多 5 句，語氣親切，指出關鍵錯誤或給予肯定。
        
        --- 學生程式碼 ---
        {code_content}
        """
            
        response = client.models.generate_content(
            model="gemini-2.5-flash", # 使用較快較新的模型
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
        global last_processed_time
        if not event.is_directory and event.src_path.endswith(".ino"):
            # 防止重複觸發 (例如 IDE 存檔時可能會寫入兩次)
            current_time = time.time()
            if current_time - last_processed_time > COOLDOWN_SECONDS:
                last_processed_time = current_time
                # 在另一個執行緒處理 API 請求，以免卡住 Watchdog
                t = threading.Thread(target=analyze_code_with_gemini, args=(event.src_path,))
                t.daemon = True
                t.start()

def start_monitoring(path_to_watch):
    """ 啟動監控的主函數 """
    print(f"[Code Monitor] 啟動監控，路徑：{path_to_watch}")
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