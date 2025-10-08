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
    Fan, sinf va mavzu asosida o‘qituvchilar uchun DARS ISHLANMA tuzadi.
    Har bir bosqichda metodik rang-baranglik (interfaol usullar, amaliy topshiriqlar, refleksiya va h.k.) mavjud.
    """
    client = _get_client()
    if client is None:
        return "Dars ishlanma yaratishda xatolik yuz berdi: OPENAI API kaliti topilmadi."

    prompt = f"""
Fan: {subject}
Sinf: {grade}
Mavzu: {topic}

🎓 DARS ISHLANMA TUZILMASI (METODIK RANG-BARANGLIK BILAN):

1. Mavzu nomi
2. Maqsadlar:
   - Ta’limiy
   - Tarbiyaviy
   - Rivojlantiruvchi
3. Dars turi (yangi bilim, aralash, amaliy, mustahkamlash va h.k.)
4. Jihozlar va ko‘rgazmali vositalar
5. Metodik yondashuvlar:
   - Aqliy hujum
   - Blits-so‘rov
   - Klaster usuli
   - Juftlikda ishlash
   - Rolli o‘yin
   - Refleksiya texnikalari (masalan: "Men bugun bildimki...", "3 ta muhim g‘oya")
6. Darsning borishi (bosqichma-bosqich):
   - Kirish qismi: motivatsiya, aqliy hujum, maqsadni aniqlash
   - Asosiy qism: yangi mavzuni bayon qilish (misollar, izohlar, formulalar tushunarli qilib), interfaol topshiriqlar
   - Mustahkamlash: amaliy mashqlar, testlar, savol-javoblar, muammoli holatlar
   - Yakuniy qism: refleksiya, baholash, umumlashtirish
   - Uyga vazifa: ijodiy topshiriq yoki amaliy mashq
7. Kutilayotgan natijalar
8. Baholash mezonlari
9. Qo‘shimcha topshiriqlar (ixtiyoriy): loyiha, rasm, tajriba, dramatizatsiya va boshqalar

📌 TALABLAR:
- Dars ishlanmada misollar, tushuntirishlar va o‘quvchi faoliyatini batafsil yozing.
- Formulalarni o‘qituvchilar uchun tushunarli, izohli tarzda yozing (masalan: “Bu yerda S — yuzasi, a va b — tomonlar uzunligi”).
- Har bosqichda kamida 2 ta interfaol metod yoki o‘yinli topshiriq bo‘lsin.
- Umumiy hajmi katta bo‘lishi kerak (kamida 500 KB atrofida matn chiqsin).
- Rasmiy, metodik va o‘qituvchi uchun qulay tilda yozilsin.
"""

    try:
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=float(TEMPERATURE),
            max_tokens=int(MAX_TOKENS)
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Dars ishlanma yaratishda xatolik yuz berdi: {str(e)}"

