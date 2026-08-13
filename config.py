import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_BASE_URL = os.getenv(
    "AI_BASE_URL",
    "https://api.groq.com/openai/v1"
)
AI_MODEL = os.getenv(
    "AI_MODEL",
    "llama-3.3-70b-versatile"
)

PERSONAL_MIN_MESSAGES = int(
    os.getenv("PERSONAL_MIN_MESSAGES", "10")
)

PERSONAL_MAX_MESSAGES = int(
    os.getenv("PERSONAL_MAX_MESSAGES", "20")
)

GROUP_POLL_MESSAGES = int(
    os.getenv("GROUP_POLL_MESSAGES", "50")
)

POLL_DURATION_SECONDS = int(
    os.getenv("POLL_DURATION_SECONDS", "180")
)
