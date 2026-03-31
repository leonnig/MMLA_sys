import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import os
import sys

# 匯入你的模組
import behavior_analysis 
import image_detect
import eye_tracking
import keyboard_monitoring  
import audio_detect  
import mouse_tracker   
import code_monitor

class MMLADashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("MMLA 多模態學習分析 - 控制面板")
        self.root.geometry("450x280")
        self.root.attributes('-topmost', True) # 讓控制面板保持在最上層

        # 變數設定
        self.student_id = tk.StringVar(value=f"user-{int(time.time())}")
        self.arduino_path = tk.StringVar(value=r"C:\Users\Cool\Documents\Arduino\Blink")
        self.is_running = False # 紀錄是否已經啟動過執行緒

        self.show_video_var = tk.BooleanVar(value=False)

        self.create_widgets()
        # 🟢 攔截視窗右上角的「Ｘ」按鈕，將它導向我們的 quit_system 函式
        self.root.protocol("WM_DELETE_WINDOW", self.quit_system)

    def create_widgets(self):
        # 學號輸入區
        tk.Label(self.root, text="學號 (Student ID):").grid(row=0, column=0, padx=10, pady=15, sticky="e")
        tk.Entry(self.root, textvariable=self.student_id, width=30).grid(row=0, column=1, padx=10, pady=15)

        # Arduino 路徑輸入區
        tk.Label(self.root, text="Arduino 專案路徑:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        tk.Entry(self.root, textvariable=self.arduino_path, width=30).grid(row=1, column=1, padx=10, pady=5)
        tk.Button(self.root, text="瀏覽...", command=self.browse_folder).grid(row=1, column=2, padx=5)

        # 顯示攝影機畫面的核取方塊 (放在 row=2)
        tk.Checkbutton(
            self.root, text="顯示攝影機畫面 (眼動/手部辨識)", 
            variable=self.show_video_var, 
            command=self.toggle_video_display
        ).grid(row=2, column=0, columnspan=3, pady=10)

        # 控制按鈕區
        btn_frame = tk.Frame(self.root)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=20)

        self.btn_start = tk.Button(btn_frame, text="▶ 開始偵測", bg="#d4edda", width=12, command=self.start_resume_system)
        self.btn_start.pack(side=tk.LEFT, padx=10)

        self.btn_pause = tk.Button(btn_frame, text="⏸ 暫停", bg="#fff3cd", width=12, command=self.pause_system, state=tk.DISABLED)
        self.btn_pause.pack(side=tk.LEFT, padx=10)

        self.btn_stop = tk.Button(btn_frame, text="⏹ 結束系統", bg="#f8d7da", width=12, command=self.quit_system)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

    # 當打勾狀態改變時，即時更新全域變數
    def toggle_video_display(self):
        behavior_analysis.SHOW_VIDEO = self.show_video_var.get()

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            # 將路徑中的斜線轉換為 Windows 格式
            self.arduino_path.set(os.path.normpath(folder_selected))

    def start_resume_system(self):
        behavior_analysis.SYSTEM_PAUSED = False

        # 取得 UI 輸入框中目前的路徑
        current_path = self.arduino_path.get()

        # 🟢 核心修改：無論是系統剛啟動，還是換路徑後恢復，都給予 3 分鐘 (180秒) 的緩衝期
        behavior_analysis.reset_grace_period(60)
        
        if not self.is_running:
            # 第一次啟動：建立並啟動所有執行緒
            print(f"歡迎，{self.student_id.get()}！系統啟動中...")
            self.is_running = True
            
            threads = [
                threading.Thread(target=eye_tracking.eye_gaze_tracking, daemon=True),
                threading.Thread(target=audio_detect.audio_detection, daemon=True),
                threading.Thread(target=mouse_tracker.start_tracking, daemon=True),
                threading.Thread(target=keyboard_monitoring.start_listening, daemon=True),
                threading.Thread(target=image_detect.image_detection, daemon=True),
                threading.Thread(target=behavior_analysis.analyze_and_send_behavior, daemon=True),
                threading.Thread(target=code_monitor.start_monitoring, args=(self.arduino_path.get(),), daemon=True),
            ]
            for t in threads:
                t.start()
            print("所有模組已成功啟動！")
        else:
            print("系統已恢復偵測！")
            behavior_analysis.behaviour_log.append((time.time(), "System: Resumed"))
            # 🟢 核心修改：通知 code_monitor 切換到新的路徑！
            code_monitor.set_monitoring_path(current_path)

        # 更新按鈕狀態
        self.btn_start.config(state=tk.DISABLED)
        self.btn_pause.config(state=tk.NORMAL)

    def pause_system(self):
        behavior_analysis.SYSTEM_PAUSED = True
        print("系統已暫停！模型待機中...")
        
        self.btn_start.config(state=tk.NORMAL, text="▶ 恢復偵測")
        self.btn_pause.config(state=tk.DISABLED)

    def quit_system(self):
        if messagebox.askokcancel("結束確認", "確定要關閉 MMLA 系統嗎？"):
            print("系統準備關閉...")
            
            # 🟢 在徹底關閉前，執行你原本的 GCS 上傳功能！
            if behavior_analysis.behaviour_log:
                print("正在上傳行為紀錄至 GCS，請稍候...")
                try:
                    # 記得使用 self.student_id.get() 來取得使用者輸入的學號
                    behavior_analysis.upload_log_to_gcs(
                        behavior_analysis.behaviour_log, 
                        "mmla-research-data-20251020", 
                        self.student_id.get()
                    )
                    print("GCS 上傳完成！")
                except Exception as e:
                    print(f"[GCS Upload Error] 上傳失敗: {e}")

            print("關閉所有執行緒...")
            self.root.destroy()
            os._exit(0)  # 強制結束所有背景 daemon 執行緒

if __name__ == "__main__":
    root = tk.Tk()
    app = MMLADashboard(root)
    root.mainloop()