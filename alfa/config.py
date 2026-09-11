from pathlib import Path

PROJECT_ROOT = Path(r"D:\Projects\alfa")
MODELS_ROOT = PROJECT_ROOT / "models"

# Путь к модели Vosk (убедись, что она там есть!)
# Если ты скачал vosk-model-small-ru-0.22, положи его в D:\Projects\alfa\models\vosk\
VOSK_MODEL_PATH = MODELS_ROOT / "vosk" / "vosk-model-small-ru-0.22"

SAMPLE_RATE = 16000
BLOCK_SIZE = 8000

# Настройки LM Studio
LM_STUDIO_HOST = "http://localhost:1234"
LM_STUDIO_ENDPOINT = "/v1/chat/completions"
LLM_TEMPERATURE = 0.3
MAX_TOKENS = 500
INDEX_EXTENSIONS = {".docx", ".doc", ".pdf", ".xlsx", ".xls", ".pptx", ".txt"}