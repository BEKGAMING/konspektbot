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
    Dars ishlanma: har bir qadamda tushuntirish va juda ko‘p misollar, topshiriqlar bilan.
    Fayl katta hajmda bo‘lishi kerak (~500KB).
    """
    client = _get_client()
    if not client:
        return "❌ Dars ishlanma yaratishda xatolik: OPENAI API kaliti topilmadi."

    prompt = f"""
Fan: {subject}
Sinf: {grade}
Mavzu: {topic}

🎓 MAQSAD:
Sinf uchun juda batafsil DARS ISHLANMA tuzing.
Faqat tushuntirish, misollar, yechimlar va topshiriqlar bo‘lsin.
Nazariy qismlar qisqagina, lekin har bir qadam amaliy misol va izoh bilan to‘ldirilgan bo‘lishi shart.
Matn hajmi katta bo‘lishi kerak (ko‘p misollar, ko‘p topshiriqlar).

📘 STRUKTURA:

1. Mavzu nomi
2. Kirish (1-2 gap)
3. Asosiy tushuntirish:
   - Har bir tushunchani alohida misol bilan tushuntiring
   - Har 2–3 jumladan keyin yangi misol keltiring
   - Har misolni yechim bilan yozing
   - Har misoldan keyin 2–3 o‘xshash topshiriq yarating
4. Mustaqil ishlash uchun mashqlar (kamida 10 ta)
5. Yechimlar (bosqichma-bosqich tushuntirilgan holda)
6. Qo‘shimcha topshiriqlar (ijodiy yoki murakkabroq)
7. Uyga vazifa (kamida 5 ta topshiriq)
8. Yakuniy xulosa (1–2 gap)

🧮 TALABLAR:
- Juda ko‘p misollar yozing, har biri to‘liq tushuntirilgan bo‘lsin.
- Har bir formula matn ko‘rinishida yozilsin (masalan, S = a * b)
- Har bir tushunchaga kamida 3 misol yozing.
- “Misol:”, “Yechim:”, “Topshiriq:” sarlavhalarini aniq ko‘rsating.
- Dars ishlanma hajmi katta bo‘lishi uchun kamida 1000+ satrga yaqin matn hosil qiling.
"""

    try:
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "Siz O‘zbekiston o‘qituvchilari uchun tajribali metodist-o‘qituvchisiz."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,  # Ko‘proq ijodiylik
            max_tokens=MAX_TOKENS,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Dars ishlanma yaratishda xatolik: {str(e)}"
