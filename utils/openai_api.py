# utils/openai_api.py
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
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")  # Sizning .env orqali o'zgartirishingiz mumkin
try:
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.5"))
except Exception:
    TEMPERATURE = 0.5
try:
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))
except Exception:
    MAX_TOKENS = 4000

# === OpenAI klientini olish (lazy) ===
def _get_client() -> Optional[OpenAI]:
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY mavjud emas (env o'zgaruvchisi).")
        return None
    try:
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        logger.exception("OpenAI klientini yaratishda xatolik: %s", e)
        return None

# === LaTeX / matematik ifodalarni sodda qilib chiqaruvchi yordamchi funksiyalar ===
_SUP_MAP = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "-": "⁻", "+": "⁺"
}

def _to_superscript(s: str) -> str:
    """Matndagi raqamlarni (masalan 12) superscriptga o'giradi (1→¹ 2→²)..."""
    out = []
    for ch in s:
        out.append(_SUP_MAP.get(ch, ch))
    return "".join(out)

def _replace_superscripts(text: str) -> str:
    # Pattern: ^{...} yoki ^x
    def _braced(m):
        inner = m.group(1)
        inner_clean = re.sub(r"\s+", "", inner)
        return _to_superscript(inner_clean)

    text = re.sub(r"\^\{([^}]+)\}", lambda m: _braced(m), text)
    # simple: x^2  -> x²
    text = re.sub(r"([A-Za-z0-9\)])\^([0-9])", lambda m: m.group(1) + _to_superscript(m.group(2)), text)
    return text

def _clean_latex(text: str) -> str:
    """
    LaTeX va matematik belgilarni oddiy, o'qilishi oson shaklga o'tkazadi.
    Maqsad: o'qituvchilar uchun oddiy matn yoki unicode belgilar bilan ko'rsatish.
    """
    if not text:
        return text

    # 1) olib tashlash: \( \), $ $, $$ $$
    text = re.sub(r"\$\$(.*?)\$\$", r"\1", text, flags=re.S)
    text = re.sub(r"\$(.*?)\$", r"\1", text, flags=re.S)
    text = re.sub(r"\\\((.*?)\\\)", r"\1", text, flags=re.S)
    text = re.sub(r"\\\[(.*?)\\\]", r"\1", text, flags=re.S)

    # 2) oddiy o'rinbosarlar (frac, sqrt, leq, geq, neq, cdot, times, etc.)
    # \frac{a}{b} -> a/b
    # Qayd: nested bracelar uchun mukammal parser emas, lekin oddiy hollarda yetadi.
    text = re.sub(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"\1/\2", text)

    # \sqrt{...} -> √(...)
    text = re.sub(r"\\sqrt\s*\{([^{}]+)\}", r"√(\1)", text)

    # \left, \right ni olib tashlash
    text = re.sub(r"\\left", "", text)
    text = re.sub(r"\\right", "", text)

    # asosiy belgi almashtirishlar
    subs = {
        r"\\leq": "≤",
        r"\\geq": "≥",
        r"\\neq": "≠",
        r"\\times": "×",
        r"\\cdot": "·",
        r"\\pm": "±",
        r"\\approx": "≈",
        r"\\to": "→",
        r"\\rightarrow": "→",
        r"\\infty": "∞",
        r"\\degree": "°",
        r"\\alpha": "α", r"\\beta": "β", r"\\gamma": "γ",
        r"\\pi": "π",
    }
    for pat, repl in subs.items():
        text = re.sub(pat, repl, text)

    # a/b typed fractions: \over not common but we try
    text = re.sub(r"\\over", "/", text)

    # remove remaining common latex commands like \mathrm{...} or \text{...}
    text = re.sub(r"\\mathrm\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\\text\{([^}]+)\}", r"\1", text)

    # braces -> parenthesis where appropriate
    text = text.replace("{", "(").replace("}", ")")

    # superscripts: ^{2} or ^2 -> show unicode superscripts where possible
    text = _replace_superscripts(text)

    # remove leftover backslash-commands if any (e.g. \, \; ) but preserve words
    text = re.sub(r"\\[a-zA-Z]+\s*", "", text)

    # collapse multiple spaces and tidy up spaces around operators
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([=+\-*/×·≥≤≠±≤≥<>])\s*", r" \1 ", text)

    return text.strip()

# === Promptlar ===
SYSTEM_PROMPT_CONSPECT = (
    "Siz O‘zbekiston umumta’lim maktablari uchun metodist-o‘qituvchisiz. "
    "Foydalanuvchi bergan fan, sinf va mavzu asosida rasmiy konspekt (ish reja) tuzing. "
    "Matn rasmiy, aniq va o‘qituvchi uchun qulay bo‘lsin."
)

SYSTEM_PROMPT_LESSON = (
    "Siz tajribali metodist-o‘qituvchisiz. "
    "Dars ishlanma tuzing: ko‘p misollar, yechimlar, interfaol metodlar va o‘qituvchi uchun aniq ko‘rsatmalar bilan."
)

# === Yadro funksiyasi: umumiy so‘rov yuboruvchi yordamchi ===
def _call_chat_completions(client: OpenAI, model: str, messages: list, temperature: float, max_tokens: int):
    max_retries = 3
    backoff = 1.0
    cur_model = model
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=cur_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return resp
        except Exception as e:
            err = str(e or "")
            logger.exception("OpenAI request failed (attempt %s) model=%s: %s", attempt, cur_model, err)

            # noto'g'ri API kalit (401)
            if "invalid_api_key" in err or "Incorrect API key" in err or "401" in err:
                raise

            # model mavjud emas -> fallback
            if ("model" in err.lower() and ("not found" in err.lower() or "is not available" in err.lower())) and cur_model != "gpt-3.5-turbo":
                logger.info("Model %s mavjud emas, fallback gpt-3.5-turbo ga urinyapmiz.", cur_model)
                cur_model = "gpt-3.5-turbo"
                continue

            # rate limit yoki server xatosi -> retry
            if "429" in err or "rate limit" in err.lower() or any(code in err for code in ["500", "502", "503"]):
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise

            # boshqa xatoliklar -> qaytadan tashqariga chiqaramiz
            raise

    raise RuntimeError("OpenAI so'rovi maksimal urinishda ham muvaffaqiyatsiz tugadi.")

# === Konspekt yaratish ===
def _build_conspect_prompt(subject: str, grade: str, topic: str) -> str:
    return f"""
Fan: {subject}
Sinf: {grade}
Mavzu: {topic}

Konspekt tarkibi:
1. Mavzu nomi
2. Maqsad va vazifalar
3. Kutilayotgan o'quv natijalari
4. Asosiy tushunchalar
5. Yangi mavzuning bayoni (batafsil, qadam-baqadam)
6. Qoida/Teorema (agar mavjud bo'lsa)
7. Formulalar (tushunarli izoh bilan)
8. Misollar va ularning yechimlari
9. Mustahkamlash savollari
10. Baholash mezonlari
11. Uyga vazifa

Eslatma:
- Formulalarni LaTeX formatda emas, oddiy belgilar bilan yozing (a/b, |a| ≥ 0, √(...)).
- Agar mavzu matematika yoki fizika bilan bog'liq bo'lsa, kamida 3 misol va 2 mustaqil topshiriq qo'shing.
- Matn rasmiy va o'qituvchi uchun qulay bo'lsin.
"""

def generate_conspect(subject: str, grade: str, topic: str) -> str:
    """
    Konspekt yaratadi va natijadagi LaTeX ifodalarni soddalashtiradi.
    """
    client = _get_client()
    if not client:
        return "Konspekt yaratishda xatolik: OPENAI API kaliti o‘rnatilmagan."

    model = DEFAULT_MODEL or "gpt-4o"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_CONSPECT},
        {"role": "user", "content": _build_conspect_prompt(subject, grade, topic)}
    ]

    try:
        resp = _call_chat_completions(client, model, messages, TEMPERATURE, MAX_TOKENS)
        text = resp.choices[0].message.content.strip()
        cleaned = _clean_latex(text)
        return cleaned
    except Exception as e:
        err = str(e)
        logger.exception("generate_conspect xatolik: %s", err)
        if "invalid_api_key" in err or "Incorrect API key" in err or "401" in err:
            return (
                "Konspekt yaratishda xatolik: OpenAI API kaliti noto'g'ri yoki bekor qilingan. "
                "Environment variables (OPENAI_API_KEY) ga to'g'ri kalit joylang."
            )
        return f"Konspekt yaratishda xatolik yuz berdi: {err[:300]}"

# === Dars ishlanma (misollar va metodik rang-baranglik bilan) ===
def _build_lesson_prompt(subject: str, grade: str, topic: str) -> str:
    return f"""
Fan: {subject}
Sinf: {grade}
Mavzu: {topic}

Iltimos, quyidagi tuzilma bo'yicha batafsil DARS ISHLANMA yozing:
1) Mavzu nomi
2) Maqsad: (ta'limiy, tarbiyaviy, rivojlantiruvchi)
3) Jihozlar va ko'rgazmali materiallar
4) Metodik yondashuvlar (kamida 4 xil interfaol metod bilan)
5) Darsning borishi: (kirish, yangi mavzu, misollar bilan bayon, amaliy mashqlar, mustahkamlash)
6) Har bosqich uchun o'qituvchi va o'quvchi faoliyati (ancha batafsil)
7) Kamida 10 ta misol (turli murakkablikda) va ularning yechimlari
8) Mustahkamlash uchun 10 ta topshiriq (turli darajada)
9) Baholash mezonlari (kriteriyalar)
10) Uyga vazifa: 3-4 turdagi topshiriq har birida 10 ta misol

Eslatma:
- FORMULALARNI oddiy, tushunarli shaklda yozing.
- Har bir misolning yechimini bosqichma-bosqich yozing.
- Har bosqichda kamida 2 interfaol usul (juftlik, rolli o'yin, klaster va h.k.) taklif qiling.
- Matn rasmiy, o'qituvchi uchun tayyor bo'lsin.
"""

def generate_lesson_plan(subject: str, grade: str, topic: str) -> str:
    client = _get_client()
    if not client:
        return "Dars ishlanma yaratishda xatolik: OPENAI API kaliti o‘rnatilmagan."

    model = DEFAULT_MODEL or "gpt-4o"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_LESSON},
        {"role": "user", "content": _build_lesson_prompt(subject, grade, topic)}
    ]

    try:
        resp = _call_chat_completions(client, model, messages, TEMPERATURE, MAX_TOKENS)
        text = resp.choices[0].message.content.strip()
        cleaned = _clean_latex(text)
        return cleaned
    except Exception as e:
        err = str(e)
        logger.exception("generate_lesson_plan xatolik: %s", err)
        if "invalid_api_key" in err or "Incorrect API key" in err or "401" in err:
            return (
                "Dars ishlanma yaratishda xatolik: OpenAI API kaliti noto'g'ri yoki bekor qilingan. "
                "Iltimos, yangi kalit yarating va `OPENAI_API_KEY` ga joylang."
            )
        return f"Dars ishlanma yaratishda xatolik yuz berdi: {err[:300]}"
