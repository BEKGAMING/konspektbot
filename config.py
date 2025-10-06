# config.py
import os

# API kalitlar va sozlamalar .env (yoki Render environment) dan o‘qiladi
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CARD_NUMBER = os.getenv("CARD_NUMBER")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.4"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1500"))
