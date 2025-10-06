# utils/openai_api.py
import logging
import time
from typing import Optional
from openai import OpenAI
from config import OPENAI_API_KEY, DEFAULT_MODEL, TEMPERATURE, MAX_TOKENS

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Lazily create client (so missing key can be handled)
def _get_client() -> Optional[OpenAI]:
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is not set.")
        return None
    try:
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        logger.exception("Failed to construct OpenAI client.")
        return None

SYSTEM_PROMPT = (
    "Siz O‘zbekiston umumta'lim maktablari uchun tajribali metodist-o‘qituvchisiz. "
    "Foydalanuvchi bergan FAN, SINF va MAVZU asosida rasmiy darslik uslubida KONSPEKT tuzing. "
    "Har doim faqat foydalanuvchi bergan MAVZUGA mos javob bering. Agar mavzu boshqa fan yoki sinfga tegishli bo‘lsa — e’tibor bering va to‘g‘ri mavzuni yozing. "
)

def _build_prompt(subject: str, grade: str, topic: str) -> str:
    return f"""
Fan: {subject}
Sinf: {grade}
Mavzu: {topic}

📌 KONSPEKTNI QUYIDAGI TUZILMADA YOZING (maktab darsligi uslubida):

1. Mavzu nomi
2. Maqsad va vazifalar
3. Kutilayotgan o‘quv natijalari
4. Asosiy tushunchalar (agar kerak bo‘lsa ta’riflar bilan)
5. Yangi mavzuning bayoni (batafsil, to‘liq tushuntirish bilan)
6. Qoida yoki Teorema (agar mavjud bo‘lsa)
7. Formulalar (oddiy MATN KO‘RINISHIDA yozing, masalan: S = a * b yoki E = mc^2)
8. Misollar va yechimlar
9. Jadval yoki taqqoslash (agar kerak bo‘lsa)
10. Mustahkamlash savollari
11. Baholash mezonlari
12. Uyga vazifa

❗ MUHIM:
- Agar mavzuda formula yo‘q bo‘lsa — FORMULA bo‘limini yozmang.
- Agar qoida/teorema bo‘lmasa — YOZMANG.
- Matnni «Hurmatli o‘quvchilar» deb emas, darslikdagi kabi neytral rasmiy uslubda yozing.
- Keraksiz she’riy yoki iqtiboslarga o‘tib ketmang.

Har bir bo‘limni aniq va izchil yozing.
"""

def generate_conspect(subject: str, grade: str, topic: str) -> str:
    """
    Generate conspect text using OpenAI. Returns user-friendly error messages on failure.
    """
    client = _get_client()
    if client is None:
        return (
            "Konspekt yaratishda xatolik yuz berdi: OPENAI API kaliti aniqlanmadi. "
            "Iltimos, `OPENAI_API_KEY` muhit o‘zgaruvchisining to‘g‘ri o‘rnatilganini tekshiring "
            "yoki platform.openai.com/account/api-keys dan yangi kalit yarating."
        )

    prompt = _build_prompt(subject, grade, topic)
    model = DEFAULT_MODEL or "gpt-3.5-turbo"

    max_retries = 3
    backoff = 1.0

    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=float(TEMPERATURE),
                max_tokens=int(MAX_TOKENS)
            )
            # normal response path
            return resp.choices[0].message.content.strip()

        except Exception as e:
            err_str = str(e or "")
            logger.exception("OpenAI request failed (attempt %s): %s", attempt, err_str)

            # Common: incorrect/invalid API key (401)
            if "Incorrect API key" in err_str or "invalid_api_key" in err_str or "401" in err_str:
                return (
                    "Konspekt yaratishda xatolik yuz berdi: OpenAI API kaliti noto‘g‘ri yoki bekor qilingan. "
                    "Iltimos, to‘g‘ri kalitni `OPENAI_API_KEY` ga o‘rnating yoki yangi kalit yarating: "
                    "https://platform.openai.com/account/api-keys"
                )

            # Model not found / invalid model -> fallback once to gpt-3.5-turbo
            if ("model" in err_str.lower() and ("not found" in err_str.lower() or "is not available" in err_str.lower())) \
               and model != "gpt-3.5-turbo":
                logger.info("Model %s not available, falling back to gpt-3.5-turbo (attempt %s).", model, attempt)
                model = "gpt-3.5-turbo"
                # retry immediately with fallback model
                continue

            # Rate limit / too many requests -> retry with backoff
            if "rate limit" in err_str.lower() or "429" in err_str:
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return "Konspekt yaratishda xatolik: so‘rovlar chegarasiga yetildi. Iltimos bir ozdan keyin qayta urinib ko'ring."

            # Server/API errors -> retry a few times
            if "500" in err_str or "503" in err_str or "502" in err_str:
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return "Konspekt yaratishda xatolik: OpenAI serverida muammo yuz berdi. Keyinroq qayta urinib ko‘ring."

            # Boshqa xatoliklar: qisqacha foydalanuvchiga ko‘rsat, to‘liq loglarda saqlanadi
            short = err_str[:240].replace("\n", " ")
            return f"Konspekt yaratishda xatolik yuz berdi: {short}"

    # agar loop ichi kutilmaganda tugasa
    return "Konspekt yaratishda noma'lum xatolik yuz berdi."
