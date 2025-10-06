# handlers/payment.py

from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_payment, is_blocked
from config import ADMIN_ID
import html

router = Router()

@router.message(F.photo)
async def payment_photo_handler(msg: types.Message):
    if is_blocked(msg.from_user.id):
        return await msg.answer("⛔ Kirish cheklangan. Administrator bilan bog‘laning.")

    file_id = msg.photo[-1].file_id
    username = msg.from_user.username or ""
    user_first = msg.from_user.first_name or ""
    user_id = msg.from_user.id

    # DB ga yozish va payment_id qaytarish
    payment_id = add_payment(user_id, username, file_id)

    await msg.answer("✅ To‘lov cheki qabul qilindi. Tez orada administrator tomonidan ko‘rib chiqiladi.")

    # admin bilan bog'lanish URL: username bo'lsa t.me/username, aks holda tg://user?id=
    if username:
        contact_url = f"https://t.me/{username}"
        display_user = f"@{html.escape(username)}"
    else:
        contact_url = f"tg://user?id={user_id}"
        display_user = html.escape(user_first)

    # Inline tugmalar
    admin_buttons = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{payment_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{payment_id}")
        ],
        [
            InlineKeyboardButton(text="⛔ Bloklash", callback_data=f"block_{user_id}"),
            InlineKeyboardButton(text="📩 Bog‘lanish", url=contact_url)
        ]
    ])

    # Caption — HTML format
    caption = (
        f"💳 <b>Yangi to‘lov cheki keldi!</b>\n\n"
        f"👤 Foydalanuvchi: {display_user}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📎 Payment ID: <code>{payment_id}</code>\n\n"
        f"⚠️ Iltimos, quyidagi tugmalardan foydalaning."
    )

    await msg.bot.send_photo(
        ADMIN_ID,
        file_id,
        caption=caption,
        parse_mode="HTML",
        reply_markup=admin_buttons
    )
