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
        "🎁 Har bir yangi foydalanuvchi 3 marta bepul foydalanadi!\n"
        "🔒 Shundan so‘ng, barcha xizmatlardan foydalanish uchun 15 000 UZS to‘lov qilinadi.\n\n"
        "Boshlash uchun quyidagilardan birini tanlang 👇",
        reply_markup=main_menu()
    )

# === Limit tekshiruvi ===
async def check_limit(uid: int, msg: types.Message):
    if uid == ADMIN_ID:
        return True
    if is_premium(uid):
        return True

    free_uses = get_free_uses(uid)
    if free_uses < 3:
        increment_free_use(uid)
        await msg.answer(f"🎁 Bepul foydalanish: {free_uses + 1}/3")
        return True
    else:
        await msg.answer(
            "🎁 Sizning 3 ta bepul imkoniyatingiz tugadi.\n"
            "🔐 Xizmatdan foydalanishni davom ettirish uchun 15 000 UZS to‘lov qiling.\n"
            "💳 Karta: <code>9860 6067 4424 9933</code>\n"
            "📸 To‘lov qilib bo‘lgandan so‘ng, chek rasmini shu botga yuboring — admin tasdiqlaydi ✅",
            parse_mode="HTML"
        )
        return False


# === 📄 Yangi Konspekt ===
@router.message(F.text == "📄 Yangi Konspekt")
async def new_conspect(msg: types.Message):
    uid = msg.from_user.id
    if is_blocked(uid):
        return await msg.answer("⛔ Siz bloklangansiz.")
    if not await check_limit(uid, msg): return
    await msg.answer("Fan nomini tanlang:", reply_markup=subject_menu())
    set_state(uid, "subject")


# === 📘 Dars ishlanma ===
@router.message(F.text == "📘 Dars ishlanma yaratish")
async def new_lesson_plan_start(msg: types.Message):
    uid = msg.from_user.id
    if is_blocked(uid):
        return await msg.answer("⛔ Siz bloklangansiz.")
    if not await check_limit(uid, msg): return
    await msg.answer("Fan nomini tanlang (dars ishlanma uchun):", reply_markup=subject_menu())
    set_state(uid, "lesson_subject")


# === 📙 Metodik maslahat ===
@router.message(F.text == "📙 Metodik maslahat")
async def methodical_start(msg: types.Message):
    uid = msg.from_user.id
    if is_blocked(uid):
        return await msg.answer("⛔ Siz bloklangansiz.")
    if not await check_limit(uid, msg): return
    await msg.answer("Fan nomini kiriting (masalan: Matematika):")
    set_state(uid, "method_subject")


# === 🪄 Muammoni tahlil qilish ===
@router.message(F.text == "🪄 Muammoni tahlil qilish")
async def problem_analysis_start(msg: types.Message):
    uid = msg.from_user.id
    if is_blocked(uid):
        return await msg.answer("⛔ Siz bloklangansiz.")
    if not await check_limit(uid, msg): return
    await msg.answer(
        "🧩 Darsda duch kelgan muammoingizni yozing.\n\n"
        "Masalan:\n"
        "— O‘quvchilar mavzuni tushunmayapti.\n"
        "— Darsda vaqt yetmayapti.\n"
        "— Guruh ishlari sust kechadi va hokazo."
    )
    set_state(uid, "problem_text")


# === Asosiy text jarayoni ===
@router.message(F.text)
async def text_flow_handler(msg: types.Message):
    uid = msg.from_user.id
    state = get_state(uid)
    text = msg.text.strip()

    # --- Muammo tahlili ---
    if state == "problem_text":
        if not await check_limit(uid, msg): return
        await msg.answer("⏳ Muammo tahlil qilinmoqda, biroz kuting...")
        try:
            result = analyze_teaching_problem(text)
            set_state(uid, None)
            return await msg.answer(result, reply_markup=main_menu())
        except Exception as e:
            set_state(uid, None)
            return await msg.answer(f"❌ Xatolik: {e}", reply_markup=main_menu())

    # --- Fan / sinf / mavzu ---
    if state in ["subject", "lesson_subject", "method_subject"]:
        set_subject(uid, text)
        next_state = {"subject": "grade", "lesson_subject": "lesson_grade", "method_subject": "method_grade"}[state]
        set_state(uid, next_state)
        return await msg.answer("Sinfni tanlang:", reply_markup=grade_menu())

    if state in ["grade", "lesson_grade", "method_grade"] and text.isdigit() and 1 <= int(text) <= 11:
        next_state = {"grade": "topic", "lesson_grade": "lesson_topic", "method_grade": "method_topic"}[state]
        set_grade(uid, text)
        set_state(uid, next_state)
        return await msg.answer("Endi mavzuni kiriting:")

        # === Konspekt ===
    if state == "topic":
        free_uses = get_free_uses(uid)
        is_free = free_uses < 3
        if not await check_limit(uid, msg): return

        subject, grade, topic = get_subject(uid), get_grade(uid), text
        await msg.answer("⏳ Konspekt tayyorlanmoqda...")
        content = generate_conspect(subject, grade, topic)

        if is_premium(uid) or is_free or uid == ADMIN_ID:
            filename = create_named_docx(content, subject, topic, uid)
            save_history(uid, subject, grade, topic, filename)
            await msg.answer_document(types.FSInputFile(filename), caption="✅ Konspekt tayyor!", reply_markup=main_menu())
            try:
                os.remove(filename)
            except:
                pass
        else:
            preview = get_preview(content, 20)
            await msg.answer(
                f"📝 Konspekt preview (20%):\n\n{preview}\n\n"
                "To‘liq versiya uchun 15 000 UZS to‘lov qiling.",
                reply_markup=main_menu()
            )
        set_state(uid, None)

    # === Dars ishlanma ===
    elif state == "lesson_topic":
        free_uses = get_free_uses(uid)
        is_free = free_uses < 3
        if not await check_limit(uid, msg): return

        subject, grade, topic = get_subject(uid), get_grade(uid), text
        await msg.answer("⏳ Dars ishlanma tayyorlanmoqda...")
        plan = generate_lesson_plan(subject, grade, topic)

        if is_premium(uid) or is_free or uid == ADMIN_ID:
            filename = create_named_docx(plan, subject, topic + "_DarsIshlanma", uid)
            save_history(uid, subject, grade, topic, filename)
            await msg.answer_document(types.FSInputFile(filename), caption="✅ Dars ishlanma tayyor!", reply_markup=main_menu())
            try:
                os.remove(filename)
            except:
                pass
        else:
            preview = get_preview(plan, 20)
            await msg.answer(
                f"📘 Dars ishlanma preview (20%):\n\n{preview}\n\n"
                "Premium uchun to‘lov: 15 000 UZS.",
                reply_markup=main_menu()
            )
        set_state(uid, None)

    # === Metodik maslahat ===
    elif state == "method_topic":
        if not await check_limit(uid, msg): return
        subject, grade, topic = get_subject(uid), get_grade(uid), text
        await msg.answer("⏳ Metodik maslahat tayyorlanmoqda...")
        result = generate_methodical_advice(subject, grade, topic)
        set_state(uid, None)
        return await msg.answer(result, reply_markup=main_menu())



# === 💳 To‘lov cheki yuborish ===
@router.message(F.photo)
async def handle_payment_photo(msg: types.Message):
    user_id = msg.from_user.id
    if is_blocked(user_id):
        return await msg.answer("⛔ Siz bloklangansiz.")

    username = msg.from_user.username or "Noma’lum"
    photo_id = msg.photo[-1].file_id
    payment_id = add_payment(user_id, username, photo_id)

    await msg.answer("✅ To‘lov cheki qabul qilindi! Admin tekshiradi ⏳")

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{payment_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{payment_id}")
        ],
        [
            InlineKeyboardButton(text="📩 Foydalanuvchi bilan bog‘lanish",
                                 url=f"https://t.me/{username}" if username != "Noma’lum" else f"tg://user?id={user_id}")
        ]
    ])

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
