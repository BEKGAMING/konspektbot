# handlers/admin.py

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import (
    set_premium, block_user, get_users_count,
    get_pending_payments, approve_payment,
    get_user_id_by_username, get_last_request
)
from utils.openai_api import generate_conspect
from utils.docx_generator import create_docx
from config import ADMIN_ID

router = Router()

def is_admin(msg: types.Message) -> bool:
    return msg.from_user.id == ADMIN_ID

# --- Admin komandalar ---
@router.message(Command("admin"))
async def admin_help(msg: types.Message):
    if not is_admin(msg):
        return await msg.answer("⛔ Siz administrator emassiz.")
    await msg.answer(
        "🔐 *Admin buyruqlari:*\n\n"
        "/payments — Kutilayotgan to‘lovlar\n"
        "/users — Foydalanuvchilar soni\n"
        "/approve @username — Username bo‘yicha premium qilish\n"
        "/block @username — Username bo‘yicha bloklash\n",
        parse_mode="Markdown"
    )

# --- Payment ro‘yxati ---
@router.message(Command("payments"))
async def payments_handler(msg: types.Message):
    if not is_admin(msg): return

    payments = get_pending_payments()
    if not payments:
        return await msg.answer("✅ Hozircha kutilayotgan to‘lovlar yo‘q.")

    for p in payments:
        payment_id, user_id, username, photo_id, approved, created_at = p

        buttons = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{payment_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{payment_id}")
            ],
            [
                InlineKeyboardButton(text="⛔ Bloklash", callback_data=f"block_{user_id}"),
                InlineKeyboardButton(text="📩 Bog‘lanish", url=f"https://t.me/{username}")
            ]
        ])

        await msg.answer_photo(
            photo_id,
            caption=(
                f"💳 *To‘lov cheki*\n"
                f"👤 @{username}\n"
                f"🆔 User ID: `{user_id}`\n"
                f"📎 Payment ID: `{payment_id}`"
            ),
            parse_mode="Markdown",
            reply_markup=buttons
        )

# --- Tasdiqlash ---
@router.callback_query(F.data.startswith("approve_"))
async def approve_callback(callback: types.CallbackQuery):
    payment_id = int(callback.data.replace("approve_", ""))
    payments = get_pending_payments()
    payment = next((p for p in payments if p[0] == payment_id), None)

    if not payment:
        return await callback.answer("❌ To‘lov allaqachon ko‘rib chiqilgan.")

    user_id = payment[1]
    username = payment[2]

    # DB yangilash
    approve_payment(payment_id)
    set_premium(user_id, 1)

    # Admin uchun
    await callback.message.edit_caption(
        f"✅ *Tasdiqlandi!*\n👤 @{username}\n🆔 User ID: `{user_id}`\n🎖 Premium faollashtirildi.",
        parse_mode="Markdown"
    )
    await callback.answer("✅ Tasdiqlandi")

    # Foydalanuvchiga xabar
    await callback.bot.send_message(
        user_id,
        "🎉 Sizning premiumingiz faollashtirildi!\nEndi to‘liq konspektlarni yuklab olishingiz mumkin ✅"
    )

    # Agar oxirgi preview bo‘lsa — qayta yuborish
    last_req = get_last_request(user_id)
    if last_req:
        subject, grade, topic = last_req
        conspect = generate_conspect(subject, grade, topic)
        filename = create_docx(conspect, f"{user_id}_{subject}_{topic}.docx")
        await callback.bot.send_document(
            user_id,
            types.FSInputFile(filename),
            caption=f"♻️ Sizning oxirgi konspektingiz qayta yuborildi:\n\n📘 {subject}, {grade}-sinf\n📝 {topic}"
        )

# --- Rad etish ---
@router.callback_query(F.data.startswith("reject_"))
async def reject_callback(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        "❌ *Rad etildi.* Admin tomonidan ko‘rib chiqildi.",
        parse_mode="Markdown"
    )
    await callback.answer("❌ Rad etildi")

# --- Bloklash ---
@router.callback_query(F.data.startswith("block_"))
async def block_callback(callback: types.CallbackQuery):
    user_id = int(callback.data.replace("block_", ""))
    block_user(user_id)

    await callback.message.edit_caption(
        "⛔ *Foydalanuvchi bloklandi.*",
        parse_mode="Markdown"
    )
    await callback.answer("⛔ Bloklandi")

# --- Foydalanuvchilar soni ---
@router.message(Command("users"))
async def users_handler(msg: types.Message):
    if not is_admin(msg): return
    count = get_users_count()
    await msg.answer(f"👥 Foydalanuvchilar soni: {count}")
