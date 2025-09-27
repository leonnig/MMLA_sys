from pynput import mouse
import time
import behavior_analysis

def on_move(x, y):
    """ 每當滑鼠移動時觸發 """
    # *** 核心修改：更新滑鼠位置 ***
    behavior_analysis.update_state("mouse_position", (x, y))

def start_tracking():
    """ 啟動滑鼠追蹤 """
    print("[Mouse] Mouse tracking thread started...")
    with mouse.Listener(on_move=on_move) as listener:
        listener.join()