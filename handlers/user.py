# handlers/user.py
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import pandas as pd, os, logging
from docx import Document

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

# === /start buyrug‘i ===
@router.message(CommandStart())
async def start_handler(msg: types.Message):
    """Foydalanuvchi /start yuborganda ishlaydi"""
    user_id = msg.from_user.id
    username = msg.from_user.username

    add_user(user_id, username)

    if is_blocked(user_id):
        return await msg.answer("⛔ Sizning profilingiz bloklangan.")

    await msg.answer(
        "🎓 Assalomu alaykum!\n\n"
        "Bu bot sizga o‘qituvchilar uchun tayyor KONSPEKT, DARS ISHLANMA va METODIK MASLAHATLAR yaratib beradi. 🤖\n\n"
        "🎁 Har bir yangi foydalanuvchi 3 marta bepul foydalanadi!\n"
        "🔒 Shundan so‘ng, barcha xizmatlardan foydalanish uchun 15 000 UZS to‘lov qilinadi.\n\n"
        "Boshlash uchun quyidagilardan birini tanlang 👇",
        reply_markup=main_menu()
    )

# === 📄 Yangi Konspekt ===
@router.message(F.text == "📄 Yangi Konspekt")
async def new_conspect(msg: types.Message):
    if is_blocked(msg.from_user.id):
        return await msg.answer("⛔ Siz bloklangansiz.")
    if not await check_limit(msg.from_user.id, msg): return
    await msg.answer("Fan nomini kiriting (masalan: Matematika):")
    set_state(msg.from_user.id, "subject")

# === Boshqa buyruqlar / textlar (qisqartirilgan) ===
# ... (sening qolgan logikalaringni o‘zgartirish shart emas)

# === Excel fayldan konspekt yaratish ===
@router.message(F.text.contains("Excel fayldan"))
async def excel_instruction(msg: types.Message):
    await msg.answer(
        "📘 Excel fayldan konspekt yaratish bo‘limi.\n\n"
        "🧩 Excel faylni quyidagicha tayyorlang:\n"
        "1. Faqat bitta ustun bo‘lsin — <b>Mavzu</b> (birinchi qatorda yozing).\n"
        "2. Faylni .xlsx formatda saqlang.\n"
        "3. So‘ng faylni shu yerga yuboring 📎",
        parse_mode="HTML"
    )
    set_state(msg.from_user.id, "excel_upload")

@router.message(F.document)
async def handle_excel_file(msg: types.Message):
    user_id = msg.from_user.id
    state = get_state(user_id)
    if state != "excel_upload":
        return

    file_path = f"temp_{user_id}.xlsx"
    await msg.bot.download(msg.document, file_path)

    try:
        df = pd.read_excel(file_path)
        if df.empty or "Mavzu" not in df.columns:
            await msg.answer("❌ Faylda 'Mavzu' nomli ustun topilmadi.")
            os.remove(file_path)
            return

        topics = df["Mavzu"].dropna().tolist()
        total = len(topics)
        await msg.answer(f"⏳ {total} ta mavzu uchun konspekt yaratilmoqda...")

        topics_text = "\n".join([f"{i+1}. {t}" for i, t in enumerate(topics)])
        prompt = (
            f"Quyidagi {total} ta mavzu bo‘yicha o‘qituvchilar uchun batafsil konspekt yozing.\n\n{topics_text}"
        )

        result = generate_conspect("Umumiy fan", "Har xil sinflar", prompt)
        doc = Document()
        doc.add_heading("Yig‘ma Konspekt", level=0)
        doc.add_paragraph(result)
        output = f"{user_id}_yigma_konspekt.docx"
        doc.save(output)

        await msg.answer_document(types.FSInputFile(output), caption="✅ Yig‘ma konspekt tayyor!")
        os.remove(file_path)
        os.remove(output)

    except Exception as e:
        await msg.answer(f"❌ Xatolik: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)

# === Limit funksiyasi (alohida pastda) ===
async def check_limit(uid: int, msg: types.Message):
    if uid == ADMIN_ID or is_premium(uid):
        return True

    free_uses = get_free_uses(uid)
    if free_uses < 3:
        increment_free_use(uid)
        await msg.answer(f"🎁 Bepul foydalanish: {free_uses + 1}/3")
        return True
    else:
        await msg.answer(
            "🎁 3 ta bepul imkoniyat tugadi.\n"
            "🔐 15 000 UZS to‘lov bilan Premium faollashtiring.",
            parse_mode="HTML"
        )
        return False
