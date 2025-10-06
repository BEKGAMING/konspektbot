# utils/openai_api.py
import os
import logging
import time
from typing import Tuple, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# === Muhit sozlamalari (Render environment variables orqali) ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or ""
OPENAI_API_KEY = OPENAI_API_KEY.strip()  # olib tashlash: bosh joy/newline
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
try:
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.4))
except Exception:
    TEMPERATURE = 0.4
try:
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 1500))
except Exception:
    MAX_TOKENS = 1500

# === OpenAI client yaratuvchi ===
def _get_client() -> Optional[OpenAI]:
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY mavjud emas.")
        return None
    try:
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        logger.exception("OpenAI klientini yaratishda xatolik.")
        return None

# === Kalit validatsiyasi (test uchun) ===
def validate_key() -> Tuple[bool, str]:
    """
    Qisqacha tekshiradi: True/False va sababi (matn).
    Eslatma: bu funksiya modeli list qilib tekshiradi — safar/sovrinlar yo'q.
    """
    client = _get_client()
    if not client:
        return False, "OPENAI_API_KEY o‘rnatilmagan (environment)."

    try:
        # eng yengil so‘rov: mavjud modellarning ro‘yxatini so‘raymiz
        client.models.list()
        return True, "OK"
    except Exception as e:
        err = str(e)
        logger.exception("API kalitni tekshirishda xatolik: %s", err)
        if "invalid_api_key" in err or "Incorrect API key" in err or "401" in err:
            return False, "API kalit noto‘g‘ri yoki bekor qilingan (401 invalid_api_key)."
        return False, f"Tekshirishda xatolik: {err[:200]}"

# === System prompt ===
SYSTEM_PROMPT = (
    "Siz O‘zbekiston umumta'lim maktablari uchun tajribali metodist-o‘qituvchisiz. "
    "Foydalanuvchi bergan FAN, SINF va MAVZU asosida rasmiy darslik uslubida KONSPEKT tuzing."
)

def _build_prompt(subject: str, grade: str, topic: str) -> str:
    return f"""
Fan: {subject}
Sinf: {grade}
Mavzu: {topic}

1. Mavzu nomi
2. Maqsad va vazifalar
3. Kutilayotgan o‘quv natijalari
4. Asosiy tushunchalar
5. Yangi mavzuning bayoni
6. Qoida yoki teorema (agar mavjud bo'lsa)
7. Formulalar (matn ko'rinishida)
8. Misollar va yechimlar
9. Mustahkamlash savollari
10. Baholash mezonlari
11. Uyga vazifa
"""

def generate_conspect(subject: str, grade: str, topic: str) -> str:
    client = _get_client()
    if not client:
        return (
            "Konspekt yaratishda xatolik: OPENAI API kaliti topilmadi. "
            "Render dashboard → Environment variables ga `OPENAI_API_KEY` ni to‘g‘ri joylang."
        )

    model = DEFAULT_MODEL or "gpt-3.5-turbo"
    prompt = _build_prompt(subject, grade, topic)
    max_retries = 3
    backoff = 1.2

    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err = str(e or "")
            logger.exception("OpenAI request failed (attempt %s): %s", attempt, err)

            # 401 / noto'g'ri kalit
            if "Incorrect API key" in err or "invalid_api_key" in err or "401" in err:
                return (
                    "Konspekt yaratishda xatolik: OpenAI API kaliti noto‘g‘ri yoki bekor qilingan (401). "
                    "Iltimos, yangi kalit yarating va Render environment ga (OPENAI_API_KEY) joylang: "
                    "https://platform.openai.com/account/api-keys"
                )

            # model topilmadi → fallback
            if ("model" in err.lower() and ("not found" in err.lower() or "is not available" in err.lower())) and model != "gpt-3.5-turbo":
                logger.info("Model %s mavjud emas, gpt-3.5-turbo ga tushyapmiz", model)
                model = "gpt-3.5-turbo"
                continue

            # rate limit / server error → retry
            if "429" in err or "rate limit" in err.lower() or any(code in err for code in ["500", "502", "503"]):
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return "Konspekt yaratishda xatolik: OpenAI serverida vaqtincha muammo. Keyinroq urinib ko‘ring."

            # boshqa xatolik — qisqacha qaytarish
            short = err[:240].replace("\n", " ")
            return f"Konspekt yaratishda xatolik yuz berdi: {short}"

    return "Konspekt yaratishda noma'lum xatolik yuz berdi."
