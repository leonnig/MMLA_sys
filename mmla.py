import time
import threading
import image_detect
import eye_tracking
import keyboard_monitoring  
import audio_detect  
import mouse_tracker   
import mmla_flask
import behavior_analysis # 載入我們的核心分析模組

SERVER_URL = "http://127.0.0.1:5000/api/upload"  # 留給日後有需要接收行為分析結果的API


# 全域變數，用於控制所有執行緒的結束
running = True

def main():
    global running
    print("MMLA system starting...")

    # 將所有任務放入執行緒中，設定為 daemon=True 讓主程式結束時它們也會跟著結束
    threads = [
        # threading.Thread(target=mmla_flask.run_server, daemon=True),
        threading.Thread(target=eye_tracking.eye_gaze_tracking, daemon=True),
        threading.Thread(target=audio_detect.audio_detection, daemon=True),
        threading.Thread(target=mouse_tracker.start_tracking, daemon=True),
        threading.Thread(target=keyboard_monitoring.start_listening, daemon=True),
        threading.Thread(target=image_detect.image_detection, daemon=True),
        # *** 核心修改：啟動行為分析執行緒 ***
        threading.Thread(target=behavior_analysis.analyze_and_send_behavior, daemon=True)
    ]

    # 啟動所有執行緒
    for t in threads:
        t.start()

    print("\nAll monitoring modules have been started.")
    print("Press 'q' in any of the OpenCV windows to exit the program.\n")

    # 主執行緒在此等待，直到 running 變為 False
    # 注意：由於OpenCV視窗的按鍵偵測在各個模組中，
    # 關閉視窗會結束該執行緒，但主程式會繼續執行。
    # 這裡用一個簡單的方式讓主程式保持執行，直到手動中斷 (Ctrl+C)。
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nProgram exiting by user request (Ctrl+C)...")
        running = False
    finally:
        # Saving log data before exit
        if behavior_analysis.behaviour_log:
            behavior_analysis.save_log_to_csv(behavior_analysis.behaviour_log)

if __name__ == "__main__":
    main()