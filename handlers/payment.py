# handlers/payment.py
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.db import add_payment, is_blocked
from config import ADMIN_ID
import html
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.photo)
async def payment_photo_handler(msg: types.Message):
    if is_blocked(msg.from_user.id):
        return await msg.answer("⛔ Kirish cheklangan. Administrator bilan bog‘laning.")

    file_id = msg.photo[-1].file_id
    username = msg.from_user.username or ""
    user_first = msg.from_user.first_name or ""
    user_id = msg.from_user.id

    # DB ga yozish va payment_id olish
    try:
        payment_id = add_payment(user_id, username, file_id)
    except Exception as e:
        logger.exception("add_payment xatolik: %s", e)
        await msg.answer("❌ To‘lovni saqlashda xatolik yuz berdi. Iltimos, administrator bilan bog‘laning.")
        return

    if not payment_id:
        logger.error("add_payment returned falsy value for user %s", user_id)
        await msg.answer("❌ To‘lovni saqlashda xatolik yuz berdi.")
        return

    await msg.answer("✅ To‘lov cheki qabul qilindi. Tez orada administrator tomonidan ko‘rib chiqiladi.")

    # admin bilan bog'lanish URL va display username (xavfsiz)
    if username:
        contact_url = f"https://t.me/{username}"
        display_user = f"@{html.escape(username)}"
    else:
        contact_url = f"tg://user?id={user_id}"
        display_user = html.escape(user_first or str(user_id))

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

    caption = (
        f"💳 <b>Yangi to‘lov cheki keldi!</b>\n\n"
        f"👤 Foydalanuvchi: {display_user}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📎 Payment ID: <code>{payment_id}</code>\n\n"
        f"⚠️ Iltimos, quyidagi tugmalardan foydalaning: ✅ Tasdiqlash / ❌ Rad etish / ⛔ Bloklash"
    )

    try:
        await msg.bot.send_photo(
            ADMIN_ID,
            file_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=admin_buttons
        )
    except Exception as e:
        logger.exception("send_photo adminga muvaffaqiyatsiz: %s", e)
        # send_message fallback
        await msg.bot.send_message(ADMIN_ID, caption, parse_mode="HTML", reply_markup=admin_buttons)
