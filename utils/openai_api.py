# utils/openai_api.py
from openai import OpenAI
from config import OPENAI_API_KEY, DEFAULT_MODEL, TEMPERATURE, MAX_TOKENS

client = OpenAI(api_key=OPENAI_API_KEY)

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
    prompt = _build_prompt(subject, grade, topic)

    try:
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Konspekt yaratishda xatolik yuz berdi: {str(e)}"
