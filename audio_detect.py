from time import time, sleep

import speech_recognition as sr
import behavior_analysis

# 定義你關心的關鍵字
KEYWORDS_HELP = [
# 呼叫稱謂
    "老師", "助教", "教授", "老師請問", "助教幫忙",
    
    # 程式碼與編譯問題
    "報錯", "失敗", "錯誤", "error", "bug", "紅字", 
    "跑不動", "沒反應", "當機", "無限迴圈", "編譯失敗",
    
    # Arduino 實作專屬問題
    "燒不進去", "找不到板子", "找不到序列埠", "COM port", 
    "燈沒亮", "壞掉了", "接觸不良", "燒掉了",
    
    # 情緒與認知卡關
    "不懂", "救命", "卡住", "好難", "看不懂", "聽不懂", 
    "寫不出來", "完蛋", "死定了", "煩欸", "到底錯哪", "放棄",
    
    # 尋求協助句型
    "幫我", "怎麼辦", "請問", "幫我看一下", "教我", 
    "怎麼寫", "怎麼弄", "怎麼接", "可以幫我嗎", "幫我找bug"
]

KEYWORDS_PEER = [
# 比較與參考
    "借我", "你的", "抄一下", "一樣", "借看一下", "參考一下", 
    "你寫好了嗎", "你跑得出來嗎", "我的不行", "跟你一樣嗎", "借抄",
    
    # 共同 Debug 與確認
    "為什麼", "試試看", "對嗎", "這樣對不對", "是不是錯了", 
    "你覺得呢", "改這個", "我們試試", "少一個", "沒加到",
    
    # 指示代名詞 (討論程式碼位置)
    "你看", "這個", "哪裡", "這裡", "那個", 
    "這行", "第幾行", "這裡錯了", "上面", "下面",
    
    # Arduino 實作討論
    "接線", "麵包板", "杜邦線", "接地", "GND", "5V", 
    "電阻", "LED", "腳位", "沒接好", "短路", "接錯",
    
    # 高中生常見語氣詞/閒聊
    "好笑", "什麼鬼", "太扯了", "好白癡", "爛掉", "哭啊", "真假"
]

def record_and_recognize(recognizer, mic):
    import code_monitor
    with mic as source:
        print("[Audio] Listening...")
        # recognizer.adjust_for_ambient_noise(source, duration=0.5)
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

    with mic as source:
        print("[Audio] Calibrating microphone for ambient noise... Please wait.")
        recognizer.adjust_for_ambient_noise(source, duration=2.0) # 拉長到 2 秒讓基準更準確

    recognizer.dynamic_energy_threshold = False

    if recognizer.energy_threshold > 300:
        recognizer.energy_threshold = 200  # 強制將門檻壓低，提高敏感度

    recognizer.pause_threshold = 1.2

    print("[Audio] Audio detection thread started...")
    while True: # 讓語音偵測持續進行

        # 🟢 新增這段：系統暫停時，麥克風待機
        if behavior_analysis.SYSTEM_PAUSED:
            sleep(0.5)
            continue
        record_and_recognize(recognizer=recognizer, mic=mic)