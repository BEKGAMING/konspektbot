# handlers/admin.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import html, logging
from utils.db import (
    set_premium, block_user, get_users_count,
    get_pending_payments, approve_payment, get_payment_by_id, reject_payment
)
from config import ADMIN_ID

router = Router()
logger = logging.getLogger(__name__)

def is_admin(msg: types.Message) -> bool:
    return msg.from_user.id == ADMIN_ID

@router.message(Command("payments"))
async def payments_handler(msg: types.Message):
    if not is_admin(msg): return
    payments = get_pending_payments()
    if not payments:
        return await msg.answer("✅ Hozircha kutilayotgan to‘lovlar yo‘q.")
    for p in payments:
        payment_id, user_id, username, photo_id, approved, created_at = p
        display_user = f"@{html.escape(username)}" if username else f"user_id: {user_id}"
        buttons = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{payment_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{payment_id}")
            ],
            [
                InlineKeyboardButton(text="⛔ Bloklash", callback_data=f"block_{user_id}"),
                InlineKeyboardButton(text="📩 Bog‘lanish", url=f"https://t.me/{username}" if username else f"tg://user?id={user_id}")
            ]
        ])
        try:
            await msg.answer_photo(
                photo=photo_id,
                caption=(
                    f"💳 <b>To‘lov cheki</b>\n\n"
                    f"👤 {display_user}\n"
                    f"🆔 ID: <code>{user_id}</code>\n"
                    f"📎 Payment ID: <code>{payment_id}</code>"
                ),
                parse_mode="HTML",
                reply_markup=buttons
            )
        except Exception:
            # fallback if answer_photo signature differs
            await msg.answer(f"📎 Payment ID: {payment_id} — @{username}", reply_markup=buttons)

@router.callback_query(F.data.startswith("approve_"))
async def approve_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔ Siz admin emassiz.", show_alert=True)

    try:
        payment_id = int(callback.data.split("_", 1)[1])
    except Exception:
        return await callback.answer("❌ Noto‘g‘ri payment id.", show_alert=True)

    payment = get_payment_by_id(payment_id)
    if not payment:
        return await callback.answer("❌ To‘lov allaqachon ko‘rib chiqilgan yoki topilmadi.", show_alert=True)

    # payment: (id, user_id, username, photo_id, approved, created_at)
    if payment[4] == 1:
        return await callback.answer("❌ Bu to‘lov allaqachon tasdiqlangan.", show_alert=True)

    user_id = payment[1]
    username = payment[2] or ""

    # tasdiqlash
    approve_payment(payment_id)
    set_premium(user_id, 1)

    # captionni yangilash (HTML)
    caption = (
        f"✅ <b>Tasdiqlandi!</b>\n\n"
        f"👤 @{html.escape(username)}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🎖 Premium faollashtirildi."
    )
    try:
        await callback.message.edit_caption(caption, parse_mode="HTML")
    except Exception as e:
        logger.exception("edit_caption xato: %s", e)

    # foydalanuvchini xabardor qilish
    try:
        await callback.message.bot.send_message(
            user_id,
            "✅ Sizning to‘lovingiz tasdiqlandi va Premium aktivlashtirildi. Endi to'liq .docx fayllarni yuklab olishingiz mumkin."
        )
    except Exception as e:
        logger.exception("Foydalanuvchiga xabar yuborishda xato: %s", e)

    await callback.answer("✅ Tasdiqlandi")

@router.callback_query(F.data.startswith("reject_"))
async def reject_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔ Siz admin emassiz.", show_alert=True)

    try:
        payment_id = int(callback.data.split("_", 1)[1])
    except:
        return await callback.answer("❌ Noto‘g‘ri payment id.", show_alert=True)

    payment = get_payment_by_id(payment_id)
    if not payment:
        return await callback.answer("❌ To‘lov topilmadi yoki allaqachon ko‘rib chiqilgan.", show_alert=True)

    # DB-da rad etilgan deb belgilash
    reject_payment(payment_id)

    try:
        await callback.message.edit_caption("❌ <b>Rad etildi.</b> Admin tomonidan rad etildi.", parse_mode="HTML")
    except Exception as e:
        logger.exception("edit_caption xato: %s", e)

    # foydalanuvchiga xabar (ixtiyoriy)
    try:
        await callback.message.bot.send_message(
            payment[1],
            "❌ To‘lovingiz ma'lum sabablarga ko'ra rad etildi. Iltimos, admin bilan bog'laning."
        )
    except Exception as e:
        logger.exception("Foydalanuvchiga xabar yuborishda xato: %s", e)

    await callback.answer("❌ Rad etildi")

@router.callback_query(F.data.startswith("block_"))
async def block_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔ Siz admin emassiz.", show_alert=True)

    try:
        user_id = int(callback.data.split("_", 1)[1])
    except:
        return await callback.answer("❌ Noto‘g‘ri user id.", show_alert=True)

    block_user(user_id)

    try:
        await callback.message.edit_caption("⛔ <b>Foydalanuvchi bloklandi.</b>", parse_mode="HTML")
    except Exception as e:
        logger.exception("edit_caption xato: %s", e)

    # foydalanuvchiga xabar
    try:
        await callback.message.bot.send_message(user_id, "⛔ Siz administrator tomonidan bloklandingiz.")
    except Exception as e:
        logger.exception("Foydalanuvchiga xabar yuborishda xato: %s", e)

    await callback.answer("⛔ Bloklandi")
