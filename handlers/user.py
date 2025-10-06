# handlers/user.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.db import (
    add_user, is_premium, is_blocked, save_history,
    get_history, set_state, get_state, set_subject, get_subject,
    set_grade, get_grade, save_last_request
)
from utils.openai_api import generate_conspect
from utils.docx_generator import create_named_docx, get_preview
import os
import re

router = Router()

# ====== Asosiy Menyu ======
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📄 Yangi Konspekt"), KeyboardButton(text="📂 Mening konspektlarim")]
        ],
        resize_keyboard=True
    )

# ====== Fan tanlash ======
def subject_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Matematika"), KeyboardButton(text="Tarix")],
            [KeyboardButton(text="Ona tili"), KeyboardButton(text="Biologiya")],
            [KeyboardButton(text="Kimyo"), KeyboardButton(text="Fizika")],
            [KeyboardButton(text="Geografiya"), KeyboardButton(text="Ingliz tili")],
            [KeyboardButton(text="Tasviriy san’at"), KeyboardButton(text="Informatika")],
            [KeyboardButton(text="Boshqa fan")]
        ],
        resize_keyboard=True
    )

# ====== Sinf tanlash ======
def grade_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=str(i)) for i in range(1, 6)],
            [KeyboardButton(text=str(i)) for i in range(6, 12)]
        ],
        resize_keyboard=True
    )

# ====== Fayl nomini xavfsiz qilish ======
def _sanitize_filename(text: str) -> str:
    safe = re.sub(r"[^\w\- ]+", "", text, flags=re.UNICODE).strip().replace(" ", "_")
    return safe or "topic"

# ====== Start ======
@router.message(Command("start"))
async def start_handler(msg: types.Message):
    add_user(msg.from_user.id, msg.from_user.username)
    if is_blocked(msg.from_user.id):
        return await msg.answer("⛔ Sizning profilingiz bloklangan.")
    await msg.answer("Assalomu alaykum!\nQuyidagi menyudan tanlang:", reply_markup=main_menu())

# ====== Yangi Konspekt ======
@router.message(F.text == "📄 Yangi Konspekt")
async def new_conspect(msg: types.Message):
    if is_blocked(msg.from_user.id):
        return await msg.answer("⛔ Siz bloklangansiz.")
    await msg.answer("Fan nomini tanlang:", reply_markup=subject_menu())
    set_state(msg.from_user.id, "subject")

# ====== Fan tanlash ======
@router.message(F.text.in_(["Matematika", "Tarix", "Ona tili", "Biologiya", "Kimyo", "Fizika", "Geografiya", "Ingliz tili", "Tasviriy san’at", "Informatika", "Boshqa fan"]))
async def select_subject(msg: types.Message):
    state = get_state(msg.from_user.id)
    if state == "subject":
        if msg.text == "Boshqa fan":
            await msg.answer("Iltimos, fan nomini matn ko‘rinishida kiriting:")
        else:
            set_subject(msg.from_user.id, msg.text)
            set_state(msg.from_user.id, "grade")
            await msg.answer("Sinfni tanlang:", reply_markup=grade_menu())

# ====== Custom fan / sinf / mavzu ======
@router.message(F.text)
async def custom_or_grade_handler(msg: types.Message):
    state = get_state(msg.from_user.id)

    # --- Custom fan ---
    if state == "subject" and msg.text not in ["Matematika", "Tarix", "Ona tili", "Biologiya", "Kimyo", "Fizika", "Geografiya", "Ingliz tili", "Tasviriy san’at", "Informatika", "Boshqa fan"]:
        set_subject(msg.from_user.id, msg.text)
        set_state(msg.from_user.id, "grade")
        return await msg.answer("Sinfni tanlang:", reply_markup=grade_menu())

    # --- Sinf ---
    if state == "grade" and msg.text.isdigit() and 1 <= int(msg.text) <= 11:
        set_grade(msg.from_user.id, msg.text)
        set_state(msg.from_user.id, "topic")
        return await msg.answer("Endi mavzuni kiriting:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]], resize_keyboard=True
        ))

    # --- Mavzu ---
    if state == "topic":
        if msg.text == "🔙 Bekor qilish":
            set_state(msg.from_user.id, None)
            return await msg.answer("Bekor qilindi.", reply_markup=main_menu())

        subject = get_subject(msg.from_user.id)
        grade = get_grade(msg.from_user.id)
        topic = msg.text

        topic_for_file = "Kop_mavzular" if "\n" in topic or len(topic) > 50 else _sanitize_filename(topic)

        if is_premium(msg.from_user.id):
            conspect = generate_conspect(subject, grade, topic)
            filename = create_named_docx(conspect, subject, topic_for_file, msg.from_user.id)
            save_history(msg.from_user.id, subject, grade, topic, filename)
            await msg.answer_document(types.FSInputFile(filename), caption="✅ Konspektingiz tayyor!", reply_markup=main_menu())

            try:
                os.remove(filename)
            except:
                pass
        else:
            conspect = generate_conspect(subject, grade, topic)
            preview = get_preview(conspect, 20)
            await msg.answer(
                "📝 Konspekt preview (20%):\n\n" + preview + "\n\nTo‘liq versiya uchun premium bo‘ling.\n9860 6067 4424 9933\n5000 UZS",
                reply_markup=main_menu()
            )
            save_last_request(msg.from_user.id, subject, grade, topic)

        set_state(msg.from_user.id, None)

# ====== Tarix ======
@router.message(F.text == "📂 Mening konspektlarim")
async def history_menu(msg: types.Message):
    user_id = msg.from_user.id

    if not is_premium(user_id):
        return await msg.answer("❌ Bu bo‘lim faqat premium foydalanuvchilar uchun.", reply_markup=main_menu())

    history = get_history(user_id)
    if not history:
        return await msg.answer("📭 Siz hali birorta konspekt yaratmagansiz.", reply_markup=main_menu())

    text = "📂 Sizning konspektlaringiz:\n\n"
    for i, item in enumerate(history, start=1):
        text += f"{i}. {item[2]} / {item[3]}-sinf — {item[4]}\n"

    text += "\nQayta yuklab olish uchun raqam yuboring. Masalan: 2"
    await msg.answer(
        text,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Orqaga")]],
            resize_keyboard=True
        )
    )
    set_state(user_id, "history_select")

# ====== Tarixdan yuklab olish ======
@router.message(F.text.regexp(r"^\d+$"))
async def history_select(msg: types.Message):
    if get_state(msg.from_user.id) != "history_select":
        return

    index = int(msg.text)
    items = get_history(msg.from_user.id)
    if not items or index < 1 or index > len(items):
        return await msg.answer("❌ Noto‘g‘ri raqam. Qayta urinib ko‘ring.")

    file_path = items[index - 1][5]  # file_path
    if not os.path.exists(file_path):
        return await msg.answer("⚠️ Fayl topilmadi. U o‘chirilgan bo‘lishi mumkin.", reply_markup=main_menu())

    await msg.answer_document(types.FSInputFile(file_path), caption="♻️ Arxivdan qayta yuklab olindi.", reply_markup=main_menu())
    set_state(msg.from_user.id, None)
