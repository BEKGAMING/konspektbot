import os
import re
import time
import logging
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# === Muhit o‘zgaruvchilari ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.4"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1500"))

# === OpenAI klienti ===
def _get_client() -> Optional[OpenAI]:
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY topilmadi.")
        return None
    try:
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        logger.exception("OpenAI klientini yaratishda xatolik: %s", e)
        return None

# === Superscript / LaTeX tozalash ===
_SUP_MAP = {"0": "⁰","1": "¹","2": "²","3": "³","4": "⁴","5": "⁵","6": "⁶","7": "⁷","8": "⁸","9": "⁹","-": "⁻","+": "⁺"}
def _to_superscript(s: str) -> str:
    return "".join(_SUP_MAP.get(ch, ch) for ch in s)

def _replace_superscripts(text: str) -> str:
    text = re.sub(r"\^\{([^}]+)\}", lambda m: _to_superscript(m.group(1)), text)
    text = re.sub(r"([A-Za-z0-9\)])\^([0-9])", lambda m: m.group(1)+_to_superscript(m.group(2)), text)
    return text

def _clean_latex(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"\$\$(.*?)\$\$|\$(.*?)\$|\\\((.*?)\\\)|\\\[(.*?)\\\]", lambda m: "".join(x for x in m.groups() if x), text)
    text = re.sub(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"\1/\2", text)
    text = re.sub(r"\\sqrt\s*\{([^{}]+)\}", r"√(\1)", text)
    text = re.sub(r"\\left|\\right", "", text)
    replace_map = {
        r"\\leq": "≤", r"\\geq": "≥", r"\\neq": "≠", r"\\times": "×", r"\\cdot": "·",
        r"\\pm": "±", r"\\approx": "≈", r"\\to": "→", r"\\infty": "∞", r"\\degree": "°",
        r"\\alpha": "α", r"\\beta": "β", r"\\gamma": "γ", r"\\pi": "π"
    }
    for pat, rep in replace_map.items():
        text = re.sub(pat, rep, text)
    text = _replace_superscripts(text)
    text = re.sub(r"\\[a-zA-Z]+\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([=+\-*/×·≥≤≠±<>])\s*", r" \1 ", text)
    return text.strip()

# === Chat fallback yordamchisi ===
def _call_chat_completions(client: OpenAI, model: str, messages: list, temperature: float, max_tokens: int):
    attempts, backoff = 0, 1
    cur_model = model
    while attempts < 3:
        attempts += 1
        try:
            return client.chat.completions.create(
                model=cur_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as e:
            err = str(e).lower()
            logger.warning(f"Xatolik ({attempts}-urinish): {err}")
            if "not found" in err and cur_model != "gpt-3.5-turbo":
                cur_model = "gpt-3.5-turbo"
                continue
            if any(code in err for code in ["429","500","502","503"]):
                time.sleep(backoff)
                backoff *= 2
                continue
            raise
    raise RuntimeError("OpenAI javobi olinmadi.")

# === Konspekt ===
SYSTEM_PROMPT_CONSPECT = (
    "Siz O‘zbekiston umumta’lim maktablari uchun metodist-o‘qituvchisiz. "
    "Berilgan fan, sinf va mavzu asosida o‘qituvchi uchun aniq, tushunarli va rasmiy KONSPEKT tuzing."
)

def _build_conspect_prompt(subject: str, grade: str, topic: str) -> str:
    return f"""
Fan: {subject}
Sinf: {grade}
Mavzu: {topic}

Konspekt tuzilmasi:
1. Mavzu nomi
2. Maqsad va vazifalar
3. Kutilayotgan natijalar
4. Asosiy tushunchalar
5. Yangi mavzu bayoni (qadam-baqadam)
6. Qoida / Teorema (agar mavjud bo‘lsa)
7. Formulalar (oddiy, o‘qituvchi tushunadigan tarzda)
8. Misollar va ularning yechimlari
9. Mustahkamlash savollari
10. Baholash mezonlari
11. Uyga vazifa

Eslatma:
- Formulalar LaTeXda emas, oddiy belgilar bilan yozilsin.
- Matn soddaligi va o‘qituvchilik tili saqlansin.
"""

def generate_conspect(subject: str, grade: str, topic: str) -> str:
    client = _get_client()
    if not client:
        return "❌ Konspekt yaratishda xatolik: API kaliti yo‘q."
    try:
        resp = _call_chat_completions(
            client, DEFAULT_MODEL,
            [
                {"role": "system", "content": SYSTEM_PROMPT_CONSPECT},
                {"role": "user", "content": _build_conspect_prompt(subject, grade, topic)}
            ],
            TEMPERATURE, MAX_TOKENS
        )
        return _clean_latex(resp.choices[0].message.content.strip())
    except Exception as e:
        return f"Konspekt yaratishda xatolik yuz berdi: {str(e)}"

# === Dars ishlanma ===
SYSTEM_PROMPT_LESSON = (
    "Siz tajribali metodist-o‘qituvchisiz. "
    "O‘zbekiston o‘quvchilari uchun amaliy, interfaol va misollar bilan boyitilgan DARS ISHLANMA yozing."
)

def _build_lesson_prompt(subject: str, grade: str, topic: str) -> str:
    return f"""
Fan: {subject}
Sinf: {grade}
Mavzu: {topic}

DARS ISHLANMA TUZILMASI:
1. Mavzu nomi
2. Maqsadlar: ta’limiy, tarbiyaviy, rivojlantiruvchi
3. Jihozlar va ko‘rgazmali vositalar
4. Metodik yondashuvlar (kamida 4 ta interfaol metod bilan)
5. Darsning borishi:
   - Kirish (motivatsiya, aqliy hujum)
   - Yangi mavzu bayoni (misollar bilan tushuntirish)
   - Amaliy mashqlar (o‘quvchi ishtirokida)
   - Mustahkamlash
6. Har bosqichda o‘qituvchi va o‘quvchi faoliyati
7. Kamida 10 misol va ularning yechimlari
8. Mustahkamlash uchun 10 topshiriq
9. Baholash mezonlari
10. Uyga vazifa: ijodiy va amaliy mashqlar

Eslatma:
- Har bir formulani izohli yozing: masalan, “S — yuzasi, a va b — tomonlar”.
- Har bosqichda 2 ta interfaol usul bo‘lsin.
- Matn o‘qituvchi uchun tayyor hujjatga o‘xshasin.
"""

def generate_lesson_plan(subject: str, grade: str, topic: str) -> str:
    client = _get_client()
    if not client:
        return "❌ Dars ishlanma yaratishda xatolik: API kaliti yo‘q."
    try:
        resp = _call_chat_completions(
            client, DEFAULT_MODEL,
            [
                {"role": "system", "content": SYSTEM_PROMPT_LESSON},
                {"role": "user", "content": _build_lesson_prompt(subject, grade, topic)}
            ],
            TEMPERATURE, MAX_TOKENS
        )
        return _clean_latex(resp.choices[0].message.content.strip())
    except Exception as e:
        return f"Dars ishlanma yaratishda xatolik: {str(e)}"

# === Metodik maslahat ===
def generate_methodical_advice(subject: str, grade: str, topic: str) -> str:
    client = _get_client()
    if not client:
        return "❌ Metodik maslahat olishda xatolik: API kaliti topilmadi."

    messages = [
        {"role": "system", "content": "Siz tajribali pedagog-metodistsiz."},
        {"role": "user", "content": f"""
Fan: {subject}
Sinf: {grade}
Mavzu: {topic}

🎓 Metodik maslahat uchun:
1. 5 ta samarali metodni yozing (interfaol, ijodiy, amaliy).
2. Har bir metodning dars bosqichidagi qo‘llanishi.
3. 2 ta o‘yinli yoki interfaol mashq misoli.
4. Amaliy loyiha yoki topshiriq g‘oyasi.
5. O‘quvchi faolligini oshirish usullari.
6. O‘qituvchi yo‘l qo‘ymaydigan metodik xatoliklar.
Matn soddaligi, amaliyligi va foydaliligiga e’tibor bering.
"""}
    ]

    try:
        resp = _call_chat_completions(client, DEFAULT_MODEL, messages, 0.6, MAX_TOKENS)
        text = resp.choices[0].message.content.strip()
        return "📙 METODIK MASLAHAT 📙\n\n" + _clean_latex(text)
    except Exception as e:
        return f"❌ Metodik maslahat olishda xatolik: {str(e)}"
