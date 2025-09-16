from pynput import mouse
import time
import requests

last_t = 0
interval = 1

def on_move(x, y):
    global last_t
    now = time.time()
    if now - last_t >= interval:
        print(f"Mouse Position: ({x}, {y})")
        last_t = now

listener = mouse.Listener(on_move=on_move)
listener.start()

def start_tracking():
    print("滑鼠追蹤執行緒已啟動...")
    with mouse.Listener(on_move=on_move) as listener:
        listener.join()