# handlers/user.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.db import (
    add_user, is_premium, is_blocked, save_history,
    get_history, set_state, get_state, set_subject, get_subject,
    set_grade, get_grade, save_last_request
)
from utils.openai_api import generate_conspect, generate_lesson_plan
from utils.docx_generator import create_named_docx, get_preview
import os, re

router = Router()

# === Asosiy Menyu ===
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📄 Yangi Konspekt"), KeyboardButton(text="📘 Dars ishlanma yaratish")],
            [KeyboardButton(text="📂 Mening konspektlarim")]
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
        "Bu bot sizga o‘qituvchilar uchun tayyor KONSPEKT va DARS ISHLANMA yaratib beradi. 🤖\n\n"
        "📘 Imkoniyatlar:\n"
        "— Har qanday fan va sinf uchun tayyor konspektlar\n"
        "— Dars ishlanma tuzilmasi bo‘yicha to‘liq metodik yordam\n"
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

# === Yangi Dars Ishlanma ===
@router.message(F.text == "📘 Dars ishlanma yaratish")
async def new_lesson_plan_start(msg: types.Message):
    if is_blocked(msg.from_user.id):
        return await msg.answer("⛔ Siz bloklangansiz.")
    await msg.answer("Fan nomini tanlang (dars ishlanma uchun):", reply_markup=subject_menu())
    set_state(msg.from_user.id, "lesson_subject")

# === Fan tanlash ===
@router.message(F.text.in_(["Matematika", "Tarix", "Ona tili", "Biologiya", "Kimyo", "Fizika",
                            "Geografiya", "Ingliz tili", "Tasviriy san’at", "Informatika", "Boshqa fan"]))
async def select_subject(msg: types.Message):
    state = get_state(msg.from_user.id)
    if state in ["subject", "lesson_subject"]:
        if msg.text == "Boshqa fan":
            await msg.answer("Iltimos, fan nomini matn shaklida kiriting:")
        else:
            set_subject(msg.from_user.id, msg.text)
            set_state(msg.from_user.id, "lesson_grade" if state == "lesson_subject" else "grade")
            await msg.answer("Sinfni tanlang:", reply_markup=grade_menu())

# === Custom fan / sinf / mavzu ===
@router.message(F.text)
async def custom_or_grade_handler(msg: types.Message):
    user_id = msg.from_user.id
    state = get_state(user_id)

    # Custom fan
    if state in ["subject", "lesson_subject"] and msg.text not in [
        "Matematika", "Tarix", "Ona tili", "Biologiya", "Kimyo", "Fizika",
        "Geografiya", "Ingliz tili", "Tasviriy san’at", "Informatika", "Boshqa fan"
    ]:
        set_subject(user_id, msg.text)
        set_state(user_id, "lesson_grade" if state == "lesson_subject" else "grade")
        return await msg.answer("Sinfni tanlang:", reply_markup=grade_menu())

    # Sinfni tanlash
    if state in ["grade", "lesson_grade"] and msg.text.isdigit() and 1 <= int(msg.text) <= 11:
        set_grade(user_id, msg.text)
        set_state(user_id, "lesson_topic" if state == "lesson_grade" else "topic")
        return await msg.answer("Endi mavzuni kiriting:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]], resize_keyboard=True
        ))

    # Konspekt mavzusi
    if state == "topic":
        if msg.text == "🔙 Bekor qilish":
            set_state(user_id, None)
            return await msg.answer("Bekor qilindi.", reply_markup=main_menu())

        subject, grade, topic = get_subject(user_id), get_grade(user_id), msg.text
        topic_for_file = _sanitize_filename(topic[:60])

        if is_premium(user_id):
            text = generate_conspect(subject, grade, topic)
            filename = create_named_docx(text, subject, topic_for_file, user_id)
            save_history(user_id, subject, grade, topic, filename)
            await msg.answer_document(types.FSInputFile(filename), caption="✅ Konspekt tayyor!", reply_markup=main_menu())
            os.remove(filename)
        else:
            text = generate_conspect(subject, grade, topic)
            preview = get_preview(text, 20)
            await msg.answer(f"📝 Konspekt preview (20%):\n\n{preview}\n\nTo‘liq versiya uchun premium bo‘ling.\nTo'lov uchun Karta:\n9860 6067 4424 9933\nR.K\nShu kartaga 15000 UZS to'lov qiling\nUndan so'ng chek rasmini shu botga yuboring!\nAdmin to'lovni tasdiqlagandan so'ng, qayta uruning!", reply_markup=main_menu())
            save_last_request(user_id, subject, grade, topic)

        set_state(user_id, None)

    # Dars ishlanma mavzusi
    if state == "lesson_topic":
        if msg.text == "🔙 Bekor qilish":
            set_state(user_id, None)
            return await msg.answer("Bekor qilindi.", reply_markup=main_menu())

        subject, grade, topic = get_subject(user_id), get_grade(user_id), msg.text
        topic_for_file = _sanitize_filename(topic[:60])

        if is_premium(user_id):
            text = generate_lesson_plan(subject, grade, topic)
            filename = create_named_docx(text, subject, topic_for_file + "_DarsIshlanma", user_id)
            save_history(user_id, subject, grade, topic, filename)
            await msg.answer_document(types.FSInputFile(filename), caption="✅ Dars ishlanma tayyor!", reply_markup=main_menu())
            os.remove(filename)
        else:
            text = generate_lesson_plan(subject, grade, topic)
            preview = get_preview(text, 20)
            await msg.answer(f"📘 Dars ishlanma preview (20%):\n\n{preview}\n\nTo‘liq versiya uchun premium bo‘ling.\nTo'lov uchun Karta:\n9860 6067 4424 9933\nR.K\nShu kartaga 15000 UZS to'lov qiling\nUndan so'ng chek rasmini shu botga yuboring!\nAdmin to'lovni tasdiqlagandan so'ng, qayta uruning!", reply_markup=main_menu())
            save_last_request(user_id, subject, grade, topic)

        set_state(user_id, None)

# === Mening konspektlarim ===
@router.message(F.text == "📂 Mening konspektlarim")
async def history_menu(msg: types.Message):
    user_id = msg.from_user.id

    # --- Premium cheklovini olib tashlaymiz (agar xohlasangiz qayta yoqish mumkin)
    # if not is_premium(user_id):
    #     return await msg.answer("❌ Bu bo‘lim faqat premium foydalanuvchilar uchun.", reply_markup=main_menu())

    history = get_history(user_id)
    if not history:
        return await msg.answer("📭 Siz hali birorta konspekt yaratmagansiz.", reply_markup=main_menu())

    text = "📂 Sizning konspektlaringiz:\n\n"
    for i, item in enumerate(history, start=1):
        subject = item[2] or "Noma’lum fan"
        grade = item[3] or "?"
        topic = item[4] or "—"
        text += f"{i}. {subject} / {grade}-sinf — {topic}\n"

    text += "\n📎 Qayta yuklab olish uchun raqam yuboring (masalan: 2)\n"
    text += "🔙 Orqaga qaytish uchun 'Orqaga' tugmasini bosing."

    await msg.answer(
        text,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Orqaga")]],
            resize_keyboard=True
        )
    )
    set_state(user_id, "history_select")


# === Tarixdan yuklab olish ===
@router.message(F.text.regexp(r"^\d+$"))
async def history_select(msg: types.Message):
    user_id = msg.from_user.id
    if get_state(user_id) != "history_select":
        return  # boshqa holatlarda javob berilmaydi

    index = int(msg.text)
    items = get_history(user_id)
    if not items or index < 1 or index > len(items):
        return await msg.answer("❌ Noto‘g‘ri raqam. Qayta urinib ko‘ring.")

    file_path = items[index - 1][5]  # 6-ustun: file_path

    # --- Fayl mavjudligini tekshirish
    if not os.path.exists(file_path):
        return await msg.answer(
            "⚠️ Fayl topilmadi. Ehtimol u o‘chirilgan.\n"
            "Yangi konspekt yaratib ko‘ring yoki boshqa faylni tanlang.",
            reply_markup=main_menu()
        )

    try:
        await msg.answer_document(
            types.FSInputFile(file_path),
            caption="♻️ Arxivdan qayta yuklab olindi.",
            reply_markup=main_menu()
        )
    except Exception as e:
        await msg.answer(f"❌ Faylni yuborishda xatolik: {str(e)}", reply_markup=main_menu())

    set_state(user_id, None)


# === Orqaga qaytish ===
@router.message(F.text == "🔙 Orqaga")
async def go_back(msg: types.Message):
    set_state(msg.from_user.id, None)
    await msg.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=main_menu())
