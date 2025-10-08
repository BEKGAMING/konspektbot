# handlers/user.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.db import (
    add_user, is_premium, is_blocked, save_history,
    get_history, set_state, get_state, set_subject, get_subject,
    set_grade, get_grade, save_last_request, add_payment
)
from utils.openai_api import (
    generate_conspect, generate_lesson_plan, generate_methodical_advice
)
from utils.docx_generator import create_named_docx, get_preview
from config import ADMIN_ID
import os, re

router = Router()

# === Asosiy menyu ===
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📄 Yangi Konspekt"), KeyboardButton(text="📘 Dars ishlanma yaratish")],
            [KeyboardButton(text="📙 Metodik maslahat"), KeyboardButton(text="📂 Mening konspektlarim")]
        ],
        resize_keyboard=True
    )

# === Fan menyusi ===
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

# === Sinf menyusi ===
def grade_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=str(i)) for i in range(1, 6)],
            [KeyboardButton(text=str(i)) for i in range(6, 12)]
        ],
        resize_keyboard=True
    )

# === Fayl nomini xavfsiz qilish ===
def _sanitize_filename(text: str) -> str:
    safe = re.sub(r"[^\w\- ]+", "", text, flags=re.UNICODE).strip().replace(" ", "_")
    return safe or "topic"


# === START ===
@router.message(Command("start"))
async def start_handler(msg: types.Message):
    add_user(msg.from_user.id, msg.from_user.username)
    if is_blocked(msg.from_user.id):
        return await msg.answer("⛔ Sizning profilingiz bloklangan.")
    await msg.answer(
        "🎓 Assalomu alaykum!\n\n"
        "Bu bot sizga o‘qituvchilar uchun tayyor KONSPEKT, DARS ISHLANMA va METODIK MASLAHATLAR yaratib beradi. 🤖\n\n"
        "📘 Imkoniyatlar:\n"
        "— Har qanday fan va sinf uchun tayyor konspektlar\n"
        "— Dars ishlanma tuzilmasi bo‘yicha to‘liq metodik yordam\n"
        "— Metodik maslahatlar: interfaol metodlar, mashqlar, maslahatlar\n"
        "— Premium foydalanuvchilar uchun DOCX fayl\n\n"
        "Boshlash uchun quyidagilardan birini tanlang 👇",
        reply_markup=main_menu()
    )


# === Yangi Konspekt ===
@router.message(F.text == "📄 Yangi Konspekt")
async def new_conspect(msg: types.Message):
    if is_blocked(msg.from_user.id):
        return await msg.answer("⛔ Siz bloklangansiz.")
    await msg.answer("Fan nomini tanlang:", reply_markup=subject_menu())
    set_state(msg.from_user.id, "subject")


# === Dars ishlanma ===
@router.message(F.text == "📘 Dars ishlanma yaratish")
async def new_lesson_plan_start(msg: types.Message):
    if is_blocked(msg.from_user.id):
        return await msg.answer("⛔ Siz bloklangansiz.")
    await msg.answer("Fan nomini tanlang (dars ishlanma uchun):", reply_markup=subject_menu())
    set_state(msg.from_user.id, "lesson_subject")


# === Metodik maslahat ===
@router.message(F.text == "📙 Metodik maslahat")
async def methodical_start(msg: types.Message):
    user_id = msg.from_user.id
    if is_blocked(user_id):
        return await msg.answer("⛔ Siz bloklangansiz.")
    await msg.answer("Fan nomini kiriting (masalan: Matematika):")
    set_state(user_id, "method_subject")


# === Fan tanlash ===
@router.message(F.text.in_([
    "Matematika", "Tarix", "Ona tili", "Biologiya", "Kimyo", "Fizika",
    "Geografiya", "Ingliz tili", "Tasviriy san’at", "Informatika", "Boshqa fan"
]))
async def select_subject(msg: types.Message):
    state = get_state(msg.from_user.id)
    if state in ["subject", "lesson_subject", "method_subject"]:
        if msg.text == "Boshqa fan":
            await msg.answer("Iltimos, fan nomini matn shaklida kiriting:")
        else:
            set_subject(msg.from_user.id, msg.text)
            next_state = {
                "subject": "grade",
                "lesson_subject": "lesson_grade",
                "method_subject": "method_grade"
            }[state]
            set_state(msg.from_user.id, next_state)
            await msg.answer("Sinfni tanlang:", reply_markup=grade_menu())


# === Custom fan / sinf / mavzu ===
@router.message(F.text)
async def custom_or_grade_handler(msg: types.Message):
    user_id = msg.from_user.id
    state = get_state(user_id)

    # 1️⃣ Custom fan
    if state in ["subject", "lesson_subject", "method_subject"] and msg.text not in [
        "Matematika", "Tarix", "Ona tili", "Biologiya", "Kimyo", "Fizika",
        "Geografiya", "Ingliz tili", "Tasviriy san’at", "Informatika", "Boshqa fan"
    ]:
        set_subject(user_id, msg.text)
        next_state = {
            "subject": "grade",
            "lesson_subject": "lesson_grade",
            "method_subject": "method_grade"
        }[state]
        set_state(user_id, next_state)
        return await msg.answer("Sinfni tanlang:", reply_markup=grade_menu())

    # 2️⃣ Sinf
    if state in ["grade", "lesson_grade", "method_grade"] and msg.text.isdigit() and 1 <= int(msg.text) <= 11:
        next_state = {
            "grade": "topic",
            "lesson_grade": "lesson_topic",
            "method_grade": "method_topic"
        }[state]
        set_grade(user_id, msg.text)
        set_state(user_id, next_state)
        return await msg.answer("Endi mavzuni kiriting:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]], resize_keyboard=True
        ))

    # 3️⃣ Konspekt
    if state == "topic":
        if msg.text == "🔙 Bekor qilish":
            set_state(user_id, None)
            return await msg.answer("Bekor qilindi.", reply_markup=main_menu())

        subject, grade, topic = get_subject(user_id), get_grade(user_id), msg.text
        await msg.answer("⏳ Konspekt tayyorlanmoqda, biroz kuting...")

        text = generate_conspect(subject, grade, topic)
        if is_premium(user_id):
            filename = create_named_docx(text, subject, topic, user_id)
            save_history(user_id, subject, grade, topic, filename)
            await msg.answer_document(types.FSInputFile(filename), caption="✅ Konspekt tayyor!", reply_markup=main_menu())
            os.remove(filename)
        else:
            preview = get_preview(text, 20)
            await msg.answer(f"📝 Konspekt preview (20%):\n\n{preview}\n\nTo‘liq versiya uchun premium bo‘ling.\nKarta: 9860 6067 4424 9933", reply_markup=main_menu())
        set_state(user_id, None)

    # 4️⃣ Dars ishlanma
    if state == "lesson_topic":
        if msg.text == "🔙 Bekor qilish":
            set_state(user_id, None)
            return await msg.answer("Bekor qilindi.", reply_markup=main_menu())

        subject, grade, topic = get_subject(user_id), get_grade(user_id), msg.text
        await msg.answer("⏳ Dars ishlanma tayyorlanmoqda, biroz kuting...")

        text = generate_lesson_plan(subject, grade, topic)
        if is_premium(user_id):
            filename = create_named_docx(text, subject, topic + "_DarsIshlanma", user_id)
            save_history(user_id, subject, grade, topic, filename)
            await msg.answer_document(types.FSInputFile(filename), caption="✅ Dars ishlanma tayyor!", reply_markup=main_menu())
            os.remove(filename)
        else:
            preview = get_preview(text, 20)
            await msg.answer(f"📘 Dars ishlanma preview (20%):\n\n{preview}\n\nPremium uchun karta: 9860 6067 4424 9933", reply_markup=main_menu())
        set_state(user_id, None)

    # 5️⃣ Metodik maslahat
    if state == "method_topic":
        if msg.text == "🔙 Bekor qilish":
            set_state(user_id, None)
            return await msg.answer("Bekor qilindi.", reply_markup=main_menu())

        subject, grade, topic = get_subject(user_id), get_grade(user_id), msg.text
        await msg.answer("⏳ Metodik maslahat tayyorlanmoqda, biroz kuting...")

        advice = generate_methodical_advice(subject, grade, topic)
        set_state(user_id, None)
        await msg.answer(advice, reply_markup=main_menu())


# === To‘lov chekini qabul qilish ===
@router.message(F.photo)
async def handle_payment_photo(msg: types.Message):
    user_id = msg.from_user.id
    username = msg.from_user.username or "Noma’lum"
    photo_id = msg.photo[-1].file_id

    # To‘lovni bazaga yozamiz
    payment_id = add_payment(user_id, username, photo_id)

    # Foydalanuvchiga xabar
    await msg.answer(
        "✅ To‘lov cheki qabul qilindi!\n"
        "Admin tomonidan tekshirilgach, sizga Premium faollashtiriladi.\n"
        "Iltimos, biroz kuting ⏳"
    )

    # --- Tugmalar ---
    buttons = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{payment_id}"),
            types.InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{payment_id}")
        ],
        [
            types.InlineKeyboardButton(text="⛔ Bloklash", callback_data=f"block_{user_id}"),
            types.InlineKeyboardButton(text="📩 Bog‘lanish", url=f"https://t.me/{username}" if username != "Noma’lum" else f"tg://user?id={user_id}")
        ]
    ])

    # Admin uchun xabar
    try:
        await msg.bot.send_photo(
            ADMIN_ID,
            photo=photo_id,
            caption=(
                f"💳 <b>Yangi to‘lov!</b>\n\n"
                f"👤 Foydalanuvchi: @{username}\n"
                f"🆔 ID: <code>{user_id}</code>\n"
                f"📎 Payment ID: <code>{payment_id}</code>"
            ),
            parse_mode="HTML",
            reply_markup=buttons
        )
    except Exception as e:
        print(f"Admin xabar yuborishda xato: {e}")
