# utils/docx_generator.py
import re
import os
from docx import Document
from docx.shared import Pt

def _sanitize_filename(text: str) -> str:
    safe = re.sub(r"[^\w\- ]+", "", text, flags=re.UNICODE).strip().replace(" ", "_")
    return safe or "konspekt"

def create_docx(conspect_text: str, filename: str = "konspekt.docx"):
    # Fayl nomini xavfsiz qilish
    safe_filename = _sanitize_filename(os.path.splitext(filename)[0]) + ".docx"

    # Fayl nomini juda uzun bo‘lsa qisqartirish (max 100 belgi)
    if len(safe_filename) > 100:
        safe_filename = safe_filename[:100] + ".docx"

    doc = Document()

    for line in conspect_text.splitlines():
        line = line.rstrip()
        if not line:
            doc.add_paragraph("")  # bo'sh qatordan ham saqlaymiz
            continue

        # header bo‘lish ehtimoli
        is_header = bool(
            re.match(r"^\d+[\.\)]\s", line) or
            re.match(r"^(Mavzu|Maqsad|Kutilayotgan|Jihoz|Darsning borishi|Baholash|Uyga vazifa|Qo‘shimcha)", line) or
            line.endswith(":")
        )

        p = doc.add_paragraph()
        run = p.add_run(line)
        if is_header:
            run.bold = True
            run.font.size = Pt(14)
        else:
            run.font.size = Pt(12)

    doc.save(safe_filename)
    return safe_filename

def create_named_docx(conspect_text: str, subject: str, topic: str, user_id: int):
    # Agar topic ko‘p qatorli bo‘lsa, faqat birinchi qator yoki "Kop_mavzular" deb olamiz
    if "\n" in topic or len(topic) > 50:
        topic_clean = "Kop_mavzular"
    else:
        topic_clean = topic

    base_name = f"{user_id}_{_sanitize_filename(subject)}_{_sanitize_filename(topic_clean)}.docx"
    return create_docx(conspect_text, filename=base_name)

def get_preview(conspect_text: str, percent: int = 20):
    lines = conspect_text.splitlines()
    preview_len = max(1, len(lines) * percent // 100)
    return "\n".join(lines[:preview_len])
