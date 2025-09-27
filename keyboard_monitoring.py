from pynput import keyboard
import behavior_analysis

def on_press(key):
    """ 每當有按鍵按下時觸發 """
    # *** 核心修改：更新鍵盤為活動狀態 ***
    behavior_analysis.update_state("keyboard_active", True)

def start_listening():
    """ 啟動鍵盤監聽 """
    print("[Keyboard] Keyboard monitoring thread started...")
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()