# utils/docx_generator.py
import os
import re
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# === Fayl nomini xavfsiz qilish ===
def _sanitize_filename(text: str) -> str:
    safe = re.sub(r"[^\w\- ]+", "", text, flags=re.UNICODE).strip().replace(" ", "_")
    return safe or "konspekt"

# === Asosiy DOCX yaratish ===
def create_docx(text: str, filename: str = "konspekt.docx", title: str = None):
    # Fayl nomini xavfsiz shaklga keltirish
    safe_filename = _sanitize_filename(os.path.splitext(filename)[0]) + ".docx"
    if len(safe_filename) > 100:
        safe_filename = safe_filename[:100] + ".docx"

    doc = Document()

    # === Sarlavha (title) ===
    if title:
        title_p = doc.add_paragraph(title)
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_p.runs[0]
        title_run.bold = True
        title_run.font.size = Pt(16)
        title_run.font.color.rgb = RGBColor(0, 51, 153)
        doc.add_paragraph("")  # bo'sh qator

    # === Asosiy matn ===
    for line in text.splitlines():
        line = line.strip()
        if not line:
            doc.add_paragraph("")
            continue

        # Katta sarlavhalarni aniqlaymiz
        is_heading = bool(
            re.match(r"^\d+[\.\)]\s", line)
            or re.match(r"^(Mavzu|Maqsad|Kutilayotgan|Jihoz|Asosiy|Yangi mavzu|Qo‘shimcha|Baholash|Uyga vazifa)", line)
            or line.endswith(":")
        )

        p = doc.add_paragraph()
        run = p.add_run(line)
        if is_heading:
            run.bold = True
            run.font.size = Pt(14)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        else:
            run.font.size = Pt(12)

    doc.save(safe_filename)
    return safe_filename

# === Foydalanuvchi nomiga mos fayl yaratish ===
def create_named_docx(text: str, subject: str, topic: str, user_id: int, mode: str = "konspekt"):
    """
    mode = "konspekt" yoki "dars_ishlanma"
    """
    topic_clean = "Kop_mavzular" if "\n" in topic or len(topic) > 50 else _sanitize_filename(topic)
    base_name = f"{user_id}_{_sanitize_filename(subject)}_{topic_clean}_{mode}.docx"

    title = f"{subject} — {topic}" if mode == "konspekt" else f"{subject} ({topic}) — Dars ishlanma"
    return create_docx(text, filename=base_name, title=title)

# === Preview (20%) ===
def get_preview(text: str, percent: int = 20):
    lines = text.splitlines()
    preview_len = max(1, len(lines) * percent // 100)
    return "\n".join(lines[:preview_len])
