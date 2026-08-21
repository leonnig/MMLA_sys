from time import time, sleep

import speech_recognition as sr
import behavior_analysis

# 定義你關心的關鍵字
KEYWORDS_HELP = [
    # ── 呼叫真人助教 / 老師 ──
    "老師", "助教", "教授", "老師救我", "老師來一下", "助教來一下",
    "來幫我", "來看一下", "過來一下", "幫我看一下啦",

    # ── 編譯 / 執行錯誤 ──
    "報錯", "又報錯", "一直報錯", "錯誤", "出錯", "出錯了", "又錯了", "還是錯",
    "怎麼又錯", "error", "bug", "有bug", "紅字", "變紅色", "一堆紅字",
    "編譯失敗", "編譯錯誤", "編譯不過", "build失敗",
    "跑不動", "跑不出來", "跑不了", "不會跑", "沒反應", "沒有反應", "沒動靜",
    "當機", "卡死", "卡死了", "無限迴圈", "一直跑", "停不下來",
    "程式錯了", "哪裡有錯", "哪裡錯", "有問題", "怪怪的", "怪怪der", "很怪",

    # ── 上傳 / 燒錄 / 序列埠（對應 Arduino 燒錄） ──
    "燒不進去", "燒錄失敗", "傳不進去", "傳不上去", "上傳失敗", "上傳不了",
    "一直上傳失敗", "upload失敗", "找不到板子", "抓不到板子", "偵測不到板子",
    "找不到序列埠", "沒有序列埠", "COM", "COM port", "連不上", "連不到",
    "板子沒反應", "看不到數值", "序列埠沒東西", "監控視窗沒東西", "Serial沒東西",

    # ── LED / 燈（LAB1 / 1+ / 3） ──
    "燈沒亮", "燈不亮", "不會亮", "燈不會亮", "燈泡沒亮", "LED沒亮", "LED不亮",
    "怎麼不亮", "一直不亮", "燈一直亮", "燈不會閃", "不會閃", "閃不起來",
    "燈反了", "燈順序不對", "燈亂閃",

    # ── 觸控感測器（LAB2 / 3） ──
    "觸控沒反應", "摸了沒反應", "摸沒反應", "碰了沒反應", "感測不到",
    "觸控失靈", "觸控不準", "摸了沒亮", "一直觸發", "自己亮", "亂觸發",

    # ── 蜂鳴器（LAB4） ──
    "不會響", "沒聲音", "沒有聲音", "蜂鳴器沒響", "蜂鳴器不會響",
    "聲音很怪", "一直響", "不會唱", "音不對",

    # ── 超聲波（LAB5 / 6） ──
    "測不到距離", "距離不對", "數值不對", "數值亂跳", "數字亂跳", "一直跳",
    "讀不到", "抓不到距離", "測距怪怪的", "一直是0", "都是0", "數值是0",

    # ── 溫溼度 DHT22 ──
    "溫溼度讀不到", "溫度讀不到", "讀不到溫度", "溫度怪怪的",
    "顯示nan", "數值是nan", "抓不到溫溼度",

    # ── 硬體 / 元件壞損 ──
    "接觸不良", "壞掉了", "燒掉了", "板子壞了", "元件壞了", "沒通電", "沒電了",

    # ── 接線 / 電路卡關 ──
    "接線錯了", "不知道怎麼接", "接哪裡", "怎麼接線", "線接哪", "接反了",
    "正負極接反", "短路了", "是不是短路", "麵包板不會用",
    "電阻接哪", "跳線接哪", "杜邦線接哪", "VCC接哪", "GND接哪", "5V接哪",
    "SIG接哪", "Trig接哪", "Echo接哪",

    # ── 語法 / 函式概念卡關（對應教學內容） ──
    "怎麼用", "這個怎麼用", "這函式", "pinMode怎麼用", "digitalWrite怎麼用",
    "digitalRead怎麼用", "怎麼設定接腳", "接腳怎麼設", "delay怎麼用", "時間怎麼設",
    "if怎麼寫", "條件怎麼寫", "判斷怎麼寫", "邏輯不會", "if else不會",
    "變數怎麼宣告", "int怎麼用", "變數不會", "怎麼印出來", "Serial怎麼用",
    "tone怎麼用", "頻率怎麼設", "副函式不會", "函式怎麼寫", "函式庫怎麼用",
    "怎麼引入", "include怎麼寫", "怎麼裝函式庫", "API不會用", "看不懂文件",
    "公式怎麼算", "距離怎麼算", "怎麼換算",

    # ── 情緒 / 認知卡關 ──
    "不懂", "看不懂", "聽不懂", "搞不懂", "完全不懂", "都不懂", "看無", "霧煞煞",
    "好難", "好難喔", "太難了", "這什麼", "卡住", "卡住了", "卡關", "我卡住",
    "不會", "不會啦", "完全不會", "都不會", "不會寫", "寫不出來", "寫不下去",
    "想不出來", "不知道怎麼", "不知道怎麼寫", "不知道要幹嘛", "沒頭緒",
    "救命", "救救我", "完蛋", "完蛋了", "死定了", "沒救了",
    "放棄", "我想放棄", "不想寫了", "到底錯哪", "到底哪裡錯",
    "怎麼會這樣", "為什麼會這樣", "煩", "好煩", "煩死了", "煩欸",
    "崩潰", "要崩潰了", "我不行了", "受不了",

    # ── 直接求助句型 ──
    "幫我", "幫我一下", "幫我看", "幫我看看", "幫我找", "幫我找bug", "幫我debug",
    "幫我改", "幫忙一下", "可以幫我", "可以幫我嗎", "可以教我", "教我", "教我一下",
    "教一下", "請問", "請問一下", "我想問", "想問一下", "問一下",
    "怎麼辦", "怎麼辦啊", "該怎麼辦", "怎麼寫", "這要怎麼寫", "怎麼弄", "怎麼做",
    "這怎麼做", "這要怎麼", "這個怎麼", "有人會嗎", "誰會", "這題怎麼", "這關怎麼過",
]

KEYWORDS_PEER = [
    # ── 與同學比較 / 求看參考（多為「你…」「借我…」句型） ──
    "借我看", "借我看一下", "給我看", "給我看一下", "你的給我看", "看一下你的",
    "參考一下", "參考你的", "你寫好了嗎", "你寫到哪", "你寫完了嗎", "你做到哪",
    "你跑得出來嗎", "你跑出來了嗎", "你成功了嗎", "你會了嗎", "你的會動嗎",
    "你的可以嗎", "我的不行", "我的不會動", "我的跑不出來",
    "跟你一樣嗎", "跟你的一樣嗎", "我跟你一樣", "你怎麼寫的", "你是怎麼寫的",
    "你怎麼用的", "你是不是也", "你也這樣嗎", "你有遇到嗎", "你也卡住嗎",
    "你過了嗎", "你那邊呢", "你那邊可以嗎",

    # ── 一起檢查 / 共同 debug ──
    "這樣對不對", "這樣對嗎", "這樣可以嗎", "對不對啊", "是不是錯了", "是不是這裡",
    "是不是少", "少一個", "少了一個", "沒加到", "忘記加", "漏掉了", "漏了",
    "多打了", "打錯了", "你覺得呢", "你覺得對嗎", "你看看", "你幫我看", "你檢查一下",
    "我們試試", "我們試試看", "要不要試", "試試這個", "改改看", "改這個", "改這裡",
    "改哪裡", "要不要改", "改一下試試", "我覺得是", "我猜是", "應該是這個",
    "可能是這裡", "是不是要加", "要不要加", "加這個", "拿掉這個", "刪掉這個",

    # ── 指出程式碼位置（和同學討論行號 / 位置） ──
    "這行", "這一行", "第幾行", "第幾行錯", "這裡錯了", "這邊錯了",
    "你看這", "你看這行", "你看這裡", "就是這裡", "問題在這", "錯在這",
    "這段", "這一段", "少括號", "少分號", "這個分號", "大括號沒關",

    # ── 一起討論接線「問題」（問題導向，不放純元件名詞） ──
    "沒接好", "接錯", "接錯了", "接反", "接反了", "短路", "是不是短路",
    "接哪裡", "這條接哪", "線插哪", "插哪裡", "插錯", "正負極接反",
    "是不是接反", "你接對了嗎", "你怎麼接的", "跳線接哪",
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