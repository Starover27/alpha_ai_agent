import json
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from config import VOSK_MODEL_PATH, SAMPLE_RATE, BLOCK_SIZE

# Номер микрофона из check_mic.py (HD Webcam C310)
MICROPHONE_INDEX = 1

class VoiceListener:
    def __init__(self):
        print("👂 Загрузка модели Vosk...")
        self.model = Model(str(VOSK_MODEL_PATH))
        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        self.queue = queue.Queue()
        print("✅ Vosk готов.")

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"⚠️ Статус аудио: {status}")
        self.queue.put(bytes(indata))

    def listen(self) -> str:
        print("🎙️ Слушаю... (говори четко)")
        try:
            with sd.RawInputStream(
                samplerate=SAMPLE_RATE, 
                blocksize=BLOCK_SIZE, 
                dtype='int16',
                channels=1, 
                callback=self._audio_callback,
                device=MICROPHONE_INDEX  # ← Здесь указываем микрофон!
            ):
                while True:
                    data = self.queue.get()
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get('text', '').strip()
                        if text:
                            print(f"🗣️ Распознано: {text}")
                            return text
        except Exception as e:
            print(f"❌ Ошибка микрофона: {e}")
            return ""