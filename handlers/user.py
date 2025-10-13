# handlers/user.py
from aiogram import Router, types, F
from aiogram.filters import Command
import pandas as pd
from docx import Document
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import (
    add_user, is_premium, is_blocked, save_history,
    set_state, get_state, set_subject, get_subject,
    set_grade, get_grade, add_payment,
    get_free_uses, increment_free_use
)
from utils.openai_api import (
    generate_conspect, generate_lesson_plan, generate_methodical_advice, analyze_teaching_problem
)
from utils.docx_generator import create_named_docx, get_preview
from config import ADMIN_ID
import os, logging

router = Router()
logger = logging.getLogger(__name__)

# === Asosiy menyu ===
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📄 Yangi Konspekt"), KeyboardButton(text="📘 Dars ishlanma yaratish")],
            [KeyboardButton(text="📙 Metodik maslahat"), KeyboardButton(text="📂 Mening konspektlarim")],
            [KeyboardButton(text="🪄 Muammoni tahlil qilish"), KeyboardButton(text="📤 Excel fayldan konspekt yaratish")]
        ],
        resize_keyboard=True
    )

# === START ===
@router.message(Command("start"))
async def start_handler(msg: types.Message):
    add_user(msg.from_user.id, msg.from_user.username)
    if is_blocked(msg.from_user.id):
        return await msg.answer("⛔ Sizning profilingiz bloklangan.")
    await msg.answer(
        "🎓 Assalomu alaykum!\n\n"
        "Bu bot sizga o‘qituvchilar uchun tayyor KONSPEKT, DARS ISHLANMA va METODIK MASLAHATLAR yaratib beradi. 🤖\n\n"
        "🎁 Har bir yangi foydalanuvchi 3 marta bepul foydalanadi!\n"
        "🔒 Keyin esa, to‘liq foydalanish uchun 15 000 UZS to‘lov qilinadi.\n\n"
        "Boshlash uchun quyidagilardan birini tanlang 👇",
        reply_markup=main_menu()
    )

# === Limit tekshiruvi ===
async def check_limit(uid: int, msg: types.Message):
    if uid == ADMIN_ID or is_premium(uid):
        return True
    free_uses = get_free_uses(uid)
    if free_uses < 3:
        increment_free_use(uid)
        await msg.answer(f"🎁 Bepul foydalanish: {free_uses + 1}/3")
        return True
    await msg.answer(
        "🎁 Sizning 3 ta bepul imkoniyatingiz tugadi.\n"
        "🔐 Xizmatdan foydalanishni davom ettirish uchun 15 000 UZS to‘lov qiling.\n"
        "💳 Karta: <code>9860 6067 4424 9933</code>\n"
        "📸 To‘lov qilib bo‘lgandan so‘ng, chek rasmini shu botga yuboring — admin tasdiqlaydi ✅",
        parse_mode="HTML"
    )
    return False

# === 📤 Excel fayldan konspekt yaratish ===
@router.message(F.text == "📤 Excel fayldan konspekt yaratish")
async def excel_instruction(msg: types.Message):
    await msg.answer(
        "📘 Excel fayldan konspekt yaratish bo‘limi.\n\n"
        "🧩 Faylni quyidagicha tayyorlang:\n"
        "1️⃣ Faqat bitta ustun bo‘lsin — <b>Mavzu</b> (birinchi qatorda yozing).\n"
        "2️⃣ Quyidagicha bo‘lsin:\n\n"
        "<pre>| Mavzu |\n"
        "|----------------------|\n"
        "| Kasrlarni qo‘shish |\n"
        "| Quyosh tizimi |\n"
        "| Fe’l zamonlari |\n"
        "| Kimyoviy reaksiyalar |\n</pre>\n\n"
        "3️⃣ Faylni <b>.xlsx</b> formatda saqlang.\n"
        "4️⃣ So‘ng faylni shu yerga yuboring 📎",
        parse_mode="HTML"
    )
    set_state(msg.from_user.id, "excel_upload")

# === Excel faylni qabul qilish ===
@router.message(F.document)
async def handle_excel_file(msg: types.Message):
    uid = msg.from_user.id
    state = get_state(uid)
    if state != "excel_upload":
        return  # boshqa fayllar uchun

    if is_blocked(uid):
        return await msg.answer("⛔ Siz bloklangansiz.")
    if not await check_limit(uid, msg):
        return

    document = msg.document
    file_path = f"temp_{uid}.xlsx"
    await msg.bot.download(document, file_path)

    try:
        df = pd.read_excel(file_path)
        if "Mavzu" not in df.columns:
            await msg.answer("❌ Excel faylda 'Mavzu' nomli ustun bo‘lishi kerak.")
            os.remove(file_path)
            return

        topics = [str(t) for t in df["Mavzu"].dropna().tolist()]
        total_topics = len(topics)
        if total_topics == 0:
            await msg.answer("⚠️ Faylda birorta ham mavzu topilmadi.")
            os.remove(file_path)
            return

        if not is_premium(uid) and total_topics > 5:
            await msg.answer(
                f"⚠️ Siz {total_topics} ta mavzu yubordingiz.\n"
                "Bepul foydalanuvchilar faqat 5 ta mavzu bilan ishlay oladi.\n\n"
                "🔓 Premium olish uchun 15 000 UZS to‘lov qiling."
            )
            os.remove(file_path)
            return

        await msg.answer(f"⏳ {total_topics} ta mavzu bo‘yicha konspekt yaratilmoqda, iltimos kuting...")

        topics_text = "\n".join([f"{i+1}. {t}" for i, t in enumerate(topics)])
        prompt = (
            f"Quyidagi {total_topics} ta mavzu bo‘yicha o‘qituvchilar uchun batafsil, to‘liq, "
            f"uzun konspekt yozing. Har bir mavzu uchun sarlavha qo‘ying va punktlar bilan yozing.\n\n{topics_text}"
        )

        result_text = generate_conspect("Umumiy fanlar", "Turli sinflar", prompt)

        doc = Document()
        doc.add_heading("Yig‘ma Konspekt", 0)
        doc.add_paragraph(result_text)
        output_path = f"{uid}_yigma_konspekt.docx"
        doc.save(output_path)

        await msg.answer_document(types.FSInputFile(output_path), caption="✅ Yig‘ma konspekt tayyor!")
        os.remove(file_path)
        os.remove(output_path)
        set_state(uid, None)

    except Exception as e:
        logger.exception("Excel konspekt xatosi: %s", e)
        await msg.answer(f"❌ Xatolik: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
