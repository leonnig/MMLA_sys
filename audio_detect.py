import speech_recognition as sr
import behavior_analysis

# 定義你關心的關鍵字
KEYWORDS = ["老師", "請問", "好難"]

def record_and_recognize():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        print("[Audio] Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        except sr.WaitTimeoutError:
            # 如果長時間沒有偵測到語音，就返回，避免執行緒卡住
            return

    try:
        print("[Audio] Recognizing...")
        # 使用 Google 語音辨識 (中文)
        text = recognizer.recognize_google(audio, language='zh-tw')
        print(f"[Audio] Recognition result: {text}")
        
        # 檢查辨識結果是否包含關鍵字
        found_keyword = None
        for kw in KEYWORDS:
            if kw in text:
                found_keyword = kw
                break

        # *** 核心修改：更新中央狀態 ***
        # 無論是否找到，都更新狀態，以便清除上一個狀態
        behavior_analysis.update_state("speech_keyword", found_keyword)
    
    except sr.UnknownValueError:
        # 如果無法辨識語音，則將關鍵字狀態清空
        behavior_analysis.update_state("speech_keyword", None)
    except sr.RequestError as e:
        print(f"[Audio] Google Speech Recognition service error: {e}")
        behavior_analysis.update_state("speech_keyword", None)

def audio_detection():
    print("[Audio] Audio detection thread started...")
    while True: # 讓語音偵測持續進行
        record_and_recognize()