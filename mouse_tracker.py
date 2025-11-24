from pynput import mouse
import time
import behavior_analysis

last_update_time = 0
UPDATE_INTERVAL = 0.1  # 每 100ms 更新一次即可

def on_move(x, y):
    """ 每當滑鼠移動時觸發 """
    global last_update_time
    current_time = time.time()

    # 控制更新頻率
    if current_time - last_update_time >= UPDATE_INTERVAL:
        behavior_analysis.update_state("mouse_position", (x, y))
        last_update_time = current_time

def start_tracking():
    """ 啟動滑鼠追蹤 """
    print("[Mouse] Mouse tracking thread started...")
    with mouse.Listener(on_move=on_move) as listener:
        listener.join()