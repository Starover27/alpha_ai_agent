import pyttsx3

class VoiceSpeaker:
    def __init__(self):
        print("️ Инициализация синтезатора речи...")
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'russian' in voice.name.lower() or 'ru' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
        self.engine.setProperty('rate', 160)
        self.engine.setProperty('volume', 1.0)
        print("✅ Синтезатор готов.")

    def speak(self, text: str):
        print(f"🔊 Озвучка: {text}")
        self.engine.say(text)
        self.engine.runAndWait()