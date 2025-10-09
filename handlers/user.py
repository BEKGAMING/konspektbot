from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.db import (
    add_user, is_premium, is_blocked, save_history,
    get_history, set_state, get_state, set_subject, get_subject,
    set_grade, get_grade, save_last_request, add_payment,
    get_free_uses, increment_free_use
)
from utils.openai_api import (
    generate_conspect, generate_lesson_plan,
    generate_methodical_advice, analyze_teaching_problem
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
            [KeyboardButton(text="🪄 Muammoni tahlil qilish")]
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

# === Limit tekshiruvi ===
async def check_user_limit(msg: types.Message):
    user_id = msg.from_user.id

    # Admin har doim cheksiz
    if user_id == ADMIN_ID:
        return True

    # Premium foydalanuvchilar cheksiz
    if is_premium(user_id):
        return True

    uses = get_free_uses(user_id)
    if uses >= 3:
        await msg.answer(
            "🎁 Sizning 3 ta bepul imkoniyatingiz tugadi.\n\n"
            "🔐 Xizmatdan foydalanishni davom ettirish uchun 15 000 UZS to‘lov qiling.\n"
            "💳 Karta: 9860 6067 4424 9933\n"
            "📸 To‘lov qilib bo‘lgandan so‘ng, to‘lov cheki rasmini shu botga yuboring. "
            "Admin uni tekshiradi va Premiumni faollashtiradi."
        )
        return False

    # Foydalanuvchi bepul huquqdan foydalandi
    increment_free_use(user_id)
    return True


# === 📄 Yangi Konspekt ===
@router.message(F.text == "📄 Yangi Konspekt")
async def new_conspect(msg: types.Message):
    uid = msg.from_user.id
    if is_blocked(uid):
        return await msg.answer("⛔ Siz bloklangansiz.")
    if not await check_user_limit(msg):
        return
    await msg.answer("Fan nomini tanlang:", reply_markup=subject_menu())
    set_state(uid, "subject")


# === 📘 Dars ishlanma ===
@router.message(F.text == "📘 Dars ishlanma yaratish")
async def new_lesson_plan_start(msg: types.Message):
    uid = msg.from_user.id
    if is_blocked(uid):
        return await msg.answer("⛔ Siz bloklangansiz.")
    if not await check_user_limit(msg):
        return
    await msg.answer("Fan nomini tanlang (dars ishlanma uchun):", reply_markup=subject_menu())
    set_state(uid, "lesson_subject")


# === 📙 Metodik maslahat ===
@router.message(F.text == "📙 Metodik maslahat")
async def methodical_start(msg: types.Message):
    uid = msg.from_user.id
    if is_blocked(uid):
        return await msg.answer("⛔ Siz bloklangansiz.")
    if not await check_user_limit(msg):
        return
    await msg.answer("Fan nomini kiriting (masalan: Matematika):")
    set_state(uid, "method_subject")


# === 🪄 Muammoni tahlil qilish ===
@router.message(F.text == "🪄 Muammoni tahlil qilish")
async def problem_analysis_start(msg: types.Message):
    uid = msg.from_user.id
    if is_blocked(uid):
        return await msg.answer("⛔ Siz bloklangansiz.")
    if not await check_user_limit(msg):
        return
    await msg.answer(
        "🧩 Darsda duch kelgan muammoingizni yozing.\n\n"
        "Masalan:\n"
        "— O‘quvchilar mavzuni tushunmayapti.\n"
        "— Darsda vaqt yetmayapti.\n"
        "— Guruh ishlari sust kechadi va hokazo."
    )
    set_state(uid, "problem_text")


# === Har qanday matnli javoblar uchun universal handler ===
@router.message(F.text)
async def text_flow_handler(msg: types.Message):
    uid = msg.from_user.id
    state = get_state(uid)
    text = msg.text.strip()

    # --- Muammo tahlili ---
    if state == "problem_text":
        await msg.answer("⏳ Muammo tahlil qilinmoqda, biroz kuting...")
        result = analyze_teaching_problem(text)
        set_state(uid, None)
        return await msg.answer(result, reply_markup=main_menu())

    # --- Fan / sinf / mavzu jarayonlari ---
    if state in ["subject", "lesson_subject", "method_subject"] and text not in [
        "Matematika", "Tarix", "Ona tili", "Biologiya", "Kimyo", "Fizika",
        "Geografiya", "Ingliz tili", "Tasviriy san’at", "Informatika", "Boshqa fan"
    ]:
        set_subject(uid, text)
        next_state = {
            "subject": "grade",
            "lesson_subject": "lesson_grade",
            "method_subject": "method_grade"
        }[state]
        set_state(uid, next_state)
        return await msg.answer("Sinfni tanlang:", reply_markup=grade_menu())

    if state in ["grade", "lesson_grade", "method_grade"] and text.isdigit() and 1 <= int(text) <= 11:
        next_state = {
            "grade": "topic",
            "lesson_grade": "lesson_topic",
            "method_grade": "method_topic"
        }[state]
        set_grade(uid, text)
        set_state(uid, next_state)
        return await msg.answer("Endi mavzuni kiriting:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]], resize_keyboard=True
        ))

    # === 📄 Konspekt yaratish ===
    if state == "topic":
        if text == "🔙 Bekor qilish":
            set_state(uid, None)
            return await msg.answer("Bekor qilindi.", reply_markup=main_menu())

        subject, grade, topic = get_subject(uid), get_grade(uid), text
        await msg.answer("⏳ Konspekt tayyorlanmoqda, biroz kuting...")

        if not await check_user_limit(msg):
            return

        content = generate_conspect(subject, grade, topic)
        if is_premium(uid) or uid == ADMIN_ID:
            filename = create_named_docx(content, subject, topic, uid)
            save_history(uid, subject, grade, topic, filename)
            await msg.answer_document(types.FSInputFile(filename), caption="✅ Konspekt tayyor!", reply_markup=main_menu())
            os.remove(filename)
        else:
            preview = get_preview(content, 20)
            await msg.answer(f"📝 Konspekt preview (20%):\n\n{preview}\n\n"
                             "To‘liq versiya uchun 15 000 UZS to‘lov qiling.\n"
                             "💳 Karta: 9860 6067 4424 9933", reply_markup=main_menu())
        set_state(uid, None)

    # === 📘 Dars ishlanma ===
    elif state == "lesson_topic":
        if text == "🔙 Bekor qilish":
            set_state(uid, None)
            return await msg.answer("Bekor qilindi.", reply_markup=main_menu())

        subject, grade, topic = get_subject(uid), get_grade(uid), text
        await msg.answer("⏳ Dars ishlanma tayyorlanmoqda, biroz kuting...")

        if not await check_user_limit(msg):
            return

        plan = generate_lesson_plan(subject, grade, topic)
        if is_premium(uid) or uid == ADMIN_ID:
            filename = create_named_docx(plan, subject, topic + "_DarsIshlanma", uid)
            save_history(uid, subject, grade, topic, filename)
            await msg.answer_document(types.FSInputFile(filename), caption="✅ Dars ishlanma tayyor!", reply_markup=main_menu())
            os.remove(filename)
        else:
            preview = get_preview(plan, 20)
            await msg.answer(f"📘 Dars ishlanma preview (20%):\n\n{preview}\n\n"
                             "Premium uchun 15 000 so‘m to‘lang.\n💳 Karta: 9860 6067 4424 9933",
                             reply_markup=main_menu())
        set_state(uid, None)

    # === 📙 Metodik maslahat ===
    elif state == "method_topic":
        if text == "🔙 Bekor qilish":
            set_state(uid, None)
            return await msg.answer("Bekor qilindi.", reply_markup=main_menu())

        subject, grade, topic = get_subject(uid), get_grade(uid), text
        await msg.answer("⏳ Metodik maslahat tayyorlanmoqda, biroz kuting...")

        if not await check_user_limit(msg):
            return

        result = generate_methodical_advice(subject, grade, topic)
        set_state(uid, None)
        return await msg.answer(result, reply_markup=main_menu())
