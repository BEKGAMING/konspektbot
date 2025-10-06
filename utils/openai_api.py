import os
import logging
import time
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# === Muhitdan (Render environment) kalitlarni o‘qish ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.4))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 1500))

# === OpenAI client ===
def _get_client() -> Optional[OpenAI]:
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY environment variable not set.")
        return None
    try:
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        logger.exception("Failed to initialize OpenAI client.")
        return None

# === System prompt ===
SYSTEM_PROMPT = (
    "Siz O‘zbekiston umumta'lim maktablari uchun tajribali metodist-o‘qituvchisiz. "
    "Foydalanuvchi bergan FAN, SINF va MAVZU asosida rasmiy darslik uslubida KONSPEKT tuzing. "
    "Faqat mavzuga mos, o‘quvchilar uchun aniq, rasmiy va izchil javob bering."
)

# === Prompt shakllantirish ===
def _build_prompt(subject: str, grade: str, topic: str) -> str:
    return f"""
Fan: {subject}
Sinf: {grade}
Mavzu: {topic}

📘 KONSPEKTNI QUYIDAGI TUZILMADA YOZING:

1. Mavzu nomi
2. Maqsad va vazifalar
3. Kutilayotgan natijalar
4. Asosiy tushunchalar (zarur bo‘lsa)
5. Yangi mavzuning bayoni
6. Qoida yoki Teorema (agar mavjud bo‘lsa)
7. Formulalar (oddiy matn ko‘rinishida)
8. Misollar va yechimlar
9. Jadval yoki taqqoslash (agar kerak bo‘lsa)
10. Mustahkamlash savollari
11. Baholash mezonlari
12. Uyga vazifa
"""

# === Asosiy funksiya ===
def generate_conspect(subject: str, grade: str, topic: str) -> str:
    client = _get_client()
    if not client:
        return (
            "❌ Konspekt yaratishda xatolik yuz berdi.\n"
            "Sabab: OPENAI API kaliti topilmadi.\n"
            "Iltimos, Render.com dagi environment sozlamalarda `OPENAI_API_KEY` ni to‘g‘ri yozing."
        )

    model = DEFAULT_MODEL or "gpt-3.5-turbo"
    prompt = _build_prompt(subject, grade, topic)

    max_retries = 3
    backoff = 1.5

    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            return resp.choices[0].message.content.strip()

        except Exception as e:
            err = str(e)
            logger.exception(f"OpenAI request failed (attempt {attempt}): {err}")

            # === Kalit xatosi ===
            if "Incorrect API key" in err or "invalid_api_key" in err or "401" in err:
                return (
                    "❌ OpenAI API kaliti noto‘g‘ri yoki eskirgan.\n"
                    "Iltimos, yangi API kalit yarating: https://platform.openai.com/account/api-keys\n"
                    "va uni Render environment sozlamalariga kiriting."
                )

            # === Model xatosi ===
            if "model" in err.lower() and "not found" in err.lower():
                if model != "gpt-3.5-turbo":
                    logger.warning("Model %s not found. Fallback to gpt-3.5-turbo", model)
                    model = "gpt-3.5-turbo"
                    continue

            # === Rate limit yoki vaqtincha muammo ===
            if "429" in err or "rate limit" in err.lower() or "server" in err.lower():
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return "⚠️ OpenAI serverida vaqtincha cheklov mavjud. Keyinroq urinib ko‘ring."

            # === Boshqa xatolik ===
            return f"Konspekt yaratishda xatolik yuz berdi:\n{err[:200]}"

    return "❌ Konspekt yaratishda noma’lum xatolik yuz berdi."
