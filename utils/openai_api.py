# utils/openai_api.py
import os
import logging
import time
from typing import Tuple, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# === Muhitdan sozlamalar ===
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.4"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1500"))

# === OpenAI client yaratish ===
def _get_client() -> Optional[OpenAI]:
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY topilmadi.")
        return None
    try:
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        logger.exception("OpenAI client yaratishda xato: %s", e)
        return None

# === Kalitni test qilish uchun ===
def validate_key() -> Tuple[bool, str]:
    client = _get_client()
    if not client:
        return False, "OPENAI_API_KEY topilmadi."
    try:
        client.models.list()
        return True, "OK"
    except Exception as e:
        msg = str(e)
        if "401" in msg or "invalid_api_key" in msg:
            return False, "API kalit noto‘g‘ri yoki bloklangan (401)."
        return False, msg[:200]

# === Asosiy system prompt ===
SYSTEM_PROMPT = (
    "Siz O‘zbekiston umumta’lim maktablari uchun tajribali metodist-o‘qituvchisiz. "
    "Foydalanuvchi bergan fan, sinf va mavzu asosida o‘quvchilar uchun to‘liq, aniq va metodik jihatdan to‘g‘ri dars materiali tayyorlang."
)

# === KONSPEKT yaratish uchun ===
def _build_conspect_prompt(subject: str, grade: str, topic: str) -> str:
    return f"""
Fan: {subject}
Sinf: {grade}
Mavzu: {topic}

KONSPEKT TUZILMASI:

1. Mavzu nomi
2. Maqsad va vazifalar
3. Kutilayotgan o‘quv natijalari
4. Asosiy tushunchalar (ta’riflar bilan)
5. Yangi mavzuning bayoni
6. Qoida yoki teorema (agar bo‘lsa)
7. Formulalar (matn ko‘rinishida)
8. Misollar va yechimlar
9. Mustahkamlash savollari
10. Baholash mezonlari
11. Uyga vazifa

❗ Matnni rasmiy va darslik uslubida yozing.
"""

# === Konspekt generatsiyasi ===
def generate_conspect(subject: str, grade: str, topic: str) -> str:
    client = _get_client()
    if not client:
        return "Konspekt yaratishda xatolik: OPENAI_API_KEY topilmadi yoki noto‘g‘ri o‘rnatilgan."

    model = DEFAULT_MODEL or "gpt-3.5-turbo"
    prompt = _build_conspect_prompt(subject, grade, topic)
    retries, backoff = 3, 1.5

    for attempt in range(1, retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS
            )
            return resp.choices[0].message.content.strip()

        except Exception as e:
            err = str(e)
            logger.error("Konspekt yaratishda xato (urinish %s): %s", attempt, err)

            if "401" in err or "invalid_api_key" in err:
                return "OpenAI API kaliti noto‘g‘ri yoki bekor qilingan. Yangi kalit yarating."

            if "model" in err and "not found" in err:
                model = "gpt-3.5-turbo"
                continue

            if any(code in err for code in ["429", "500", "502", "503"]):
                if attempt < retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return "OpenAI serverida vaqtincha muammo. Keyinroq urinib ko‘ring."

            return f"Konspekt yaratishda xatolik yuz berdi: {err[:200]}"

    return "Konspekt yaratishda noma’lum xatolik yuz berdi."


# === Dars ishlanma (Lesson Plan) ===
def generate_lesson_plan(subject: str, grade: str, topic: str) -> str:
    client = _get_client()
    if not client:
        return "Dars ishlanma yaratishda xatolik: OPENAI_API_KEY topilmadi yoki noto‘g‘ri."

    model = DEFAULT_MODEL or "gpt-3.5-turbo"
    prompt = f"""
Fan: {subject}
Sinf: {grade}
Mavzu: {topic}

📘 DARS ISHLANMA TUZILMASI:

1. Mavzu nomi
2. Maqsad:
   - Ta’limiy
   - Tarbiyaviy
   - Rivojlantiruvchi
3. Dars turi (yangi bilim, mustahkamlash, aralash va boshqalar)
4. Jihozlar va ko‘rgazmali qurollar
5. Darsning borishi:
   - Kirish qismi (motivatsiya, mavzuga kirish)
   - Yangi mavzuni bayon qilish
   - Mustahkamlash
   - Baholash
   - Uyga vazifa
6. Kutilayotgan natijalar
7. Qo‘shimcha topshiriqlar (ixtiyoriy)
8. Baholash mezonlari

❗ Dars ishlanmani o‘qituvchi uchun yozing.
   Har bir bosqichda o‘qituvchi va o‘quvchi faoliyatini ajrating.
   Matn rasmiy va metodik tilda bo‘lishi kerak.
"""

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        err = str(e)
        logger.error("Dars ishlanma yaratishda xato: %s", err)

        if "401" in err or "invalid_api_key" in err:
            return "OpenAI API kaliti noto‘g‘ri yoki bekor qilingan."

        if any(code in err for code in ["429", "500", "502", "503"]):
            return "OpenAI serverida vaqtincha muammo. Keyinroq qayta urinib ko‘ring."

        return f"Dars ishlanma yaratishda xatolik yuz berdi: {err[:200]}"
