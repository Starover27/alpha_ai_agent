import sounddevice as sd

print("🎤 Доступные аудиоустройства:\n")
devices = sd.query_devices()
for i, device in enumerate(devices):
    print(f"  [{i}] {device['name']} (входов: {device['max_input_channels']})")