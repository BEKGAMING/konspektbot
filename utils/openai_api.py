import os
import logging
import time
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# === Muhit o‘zgaruvchilari ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.5"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))  # Ko‘proq tokenlar ruxsati

# === Client yaratish ===
def _get_client() -> Optional[OpenAI]:
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY mavjud emas.")
        return None
    try:
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        logger.exception("OpenAI klientini yaratishda xatolik.")
        return None

# === Konspekt ===
SYSTEM_PROMPT = (
    "Siz O‘zbekiston umumta’lim maktablari uchun metodist-o‘qituvchisiz. "
    "Foydalanuvchi bergan fan, sinf va mavzu asosida darslik uslubida rasmiy konspekt tuzing."
)

def _build_prompt(subject: str, grade: str, topic: str) -> str:
    return f"""
Fan: {subject}
Sinf: {grade}
Mavzu: {topic}

📋 KONSPEKT STRUKTURASI:
1. Mavzu nomi
2. Maqsad va vazifalar
3. Kutilayotgan natijalar
4. Asosiy tushunchalar
5. Yangi mavzuning bayoni (tushuntirish bilan)
6. Qoida yoki Teorema (agar mavjud bo‘lsa)
7. Formulalar (oddiy matn shaklida)
8. Misollar
9. Mustahkamlash savollari
10. Baholash mezonlari
11. Uyga vazifa
"""

def generate_conspect(subject: str, grade: str, topic: str) -> str:
    client = _get_client()
    if not client:
        return "❌ Konspekt yaratishda xatolik: OPENAI API kaliti topilmadi."

    prompt = _build_prompt(subject, grade, topic)
    try:
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Konspekt yaratishda xatolik: {str(e)}"

# === DARS ISHLANMA (MISOLLARGA BO‘LAK-BO‘LAK YO‘NALGAN VARIANT) ===
def generate_lesson_plan(subject: str, grade: str, topic: str) -> str:
    """
    Dars ishlanma: faqat tushuntirish, misollar, izohli formulalar va topshiriqlar bilan.
    Har bir formula oddiy o‘qituvchi uchun tushunarli tarzda yoziladi.
    """
    client = _get_client()
    if client is None:
        return "❌ Dars ishlanma yaratishda xatolik: OPENAI API kaliti topilmadi."

    prompt = f"""
Fan: {subject}
Sinf: {grade}
Mavzu: {topic}

🎓 MAQSAD:
Oddiy o‘qituvchi uchun to‘liq, tushunarli DARS ISHLANMA yarating.
Nazariya qisqa bo‘lsin, lekin har bir qadamda batafsil tushuntirish, izoh va misollar juda ko‘p bo‘lsin.
Formulalar matn ko‘rinishida emas, **tushuntirib yozilsin**:
masalan, "S = a × b" emas, balki "To‘g‘ri to‘rtburchakning yuzasi uzunlik bilan eni ko‘paytmasiga teng (S = a × b)" tarzda.

📘 DARS ISHLANMA STRUKTURASI:

1. Mavzu nomi
2. Kirish (mavzuning ahamiyati haqida 2–3 gap)
3. Asosiy qism:
   - Har bir tushunchani alohida tushuntiring
   - Har bir tushuncha uchun 3–5 ta misol yozing
   - Har misolni izoh bilan yeching
   - Formulalar berilganda ularning ma’nosini odamlarga tushunarli qilib yozing
   - Har bir formula uchun real hayotdan 1–2 misol keltiring
4. Mustaqil ishlash uchun mashqlar (kamida 10 ta)
5. Yechimlar (bosqichma-bosqich)
6. Qo‘shimcha topshiriqlar (murakkabroq misollar)
7. Uyga vazifa (kamida 5 ta topshiriq)
8. Yakuniy xulosa (1–2 gap)

🧮 TALABLAR:
- Har bir “Formula” tushuntirilgan bo‘lsin.
- Har 2–3 misoldan keyin “Xulosa:” shaklida izoh yozilsin.
- Juda batafsil yozing, har bir misol tushunarli bo‘lishi kerak.
- Hajmi katta bo‘lsin (500KB ga yaqin matn).
"""

    try:
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Siz O‘zbekiston maktablari uchun dars ishlanmalar tayyorlovchi metodist-o‘qituvchisiz. "
                        "Sizdan kutilgan narsa: o‘qituvchi va o‘quvchi uchun amaliy, izohli, misollar bilan boy dars ishlanma yozish."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.75,  # yanada ijodiyroq, tabiiy matn
            max_tokens=MAX_TOKENS,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Dars ishlanma yaratishda xatolik: {str(e)}"
