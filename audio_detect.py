import speech_recognition as sr
import behavior_analysis

# 定義你關心的關鍵字
KEYWORDS_HELP = [
    "老師", "助教", "教授", 
    "不懂", "報錯", "失敗", "救命", "卡住", "好難", 
    "幫我", "怎麼辦", "請問"
]

KEYWORDS_PEER = [
    "借我", "你看", "這個", "哪裡", "接線", 
    "為什麼", "好笑", "你的", "抄一下", "試試看", 
    "對嗎", "一樣"
]

def record_and_recognize(recognizer, mic):
    import code_monitor
    with mic as source:
        print("[Audio] Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=3, phrase_time_limit=5)
        except sr.WaitTimeoutError:
            # 如果長時間沒有偵測到語音，就返回，避免執行緒卡住
            return

    try:
        print("[Audio] Recognizing...")
        # 使用 Google 語音辨識 (中文)
        text = recognizer.recognize_google(audio, language='zh-tw')
        print(f"[Audio] Recognition result: {text}")
        
        # --- 分類邏輯 ---
        intent = "Silence"
        found_keyword = None
        
        # 檢查辨識結果是否包含關鍵字

        for kw in KEYWORDS_HELP:
            if kw in text:
                intent = "Help_Seeking"
                found_keyword = kw
                break
        if intent == "Silence":
            for kw in KEYWORDS_PEER:
                if kw in text:
                    intent = "Peer_Discussion"
                    found_keyword = kw
                    break

        # 無論是否找到，都更新狀態，以便清除上一個狀態
        if intent != "Silence":
            print(f"[Audio Detected] 類別: {intent}(關鍵字: {found_keyword})")
            behavior_analysis.update_state("speech_keyword", found_keyword)
            behavior_analysis.update_state("speech_intent", intent)

            print(f"[Audio Trigger] 偵測到語音意圖，立即觸發 AI...")
            try:
                code_monitor.trigger_ai_feedback(reason="speech")
            except Exception as e:
                print(f"[Audio Trigger Error] 無法觸發 AI: {e}")
        
        else: # Silence 情況
            pass

    
    except sr.UnknownValueError:
        # 如果無法辨識語音，則將關鍵字狀態清空
        behavior_analysis.update_state("speech_keyword", None)
    except sr.RequestError as e:
        print(f"[Audio] Google Speech Recognition service error: {e}")
        behavior_analysis.update_state("speech_keyword", None)

def audio_detection():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("[Audio] Audio detection thread started...")
    while True: # 讓語音偵測持續進行
        record_and_recognize(recognizer=recognizer, mic=mic)