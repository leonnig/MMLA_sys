import speech_recognition as sr

def record_and_recognize():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("Please start talking...")

    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
        
        print("Speech recognition in progress...")
        
        # This is for chinese recognition,  
        # you can change the language parameter in recognize_google() for other languages
        text = recognizer.recognize_google(audio, language='zh-tw') 
        print("Recognition results：", text)
    
    except sr.UnknownValueError:
        print("Unable to recognize audio")
    except sr.RequestError as e:
        print(f"Unable to connect to Google Speech Recognition service：{e}")

def audio_detection():
    while True:
        record_and_recognize()
        print("====== Record again ======")