import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from audio.listener import VoiceListener
from audio.tts import VoiceSpeaker
from brain.agent import Agent

def main():
    print("\n" + "="*50)
    print("  🚀 ЗАПУСК АССИСТЕНТА 'АЛЬФА'")
    print("="*50 + "\n")

    listener = VoiceListener()
    speaker = VoiceSpeaker()
    agent = Agent()

    greeting = "Привет! Я Альфа. Я готова к работе. Чем могу помочь?"
    print(f"🤖 {greeting}")
    speaker.speak(greeting)

    while True:
        try:
            text = listener.listen()
            if not text: continue

            print("\n🧠 Обрабатываю запрос...")
            response = agent.process_command(text)

            print(f"\n Альфа: {response}")
            speaker.speak(response)

        except KeyboardInterrupt:
            print("\n👋 Завершение работы...")
            break
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            speaker.speak("Произошла ошибка.")

if __name__ == "__main__":
    main()