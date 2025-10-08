# handlers/admin.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import html, logging, os
from utils.db import (
    set_premium, block_user, unblock_user, get_users_count, get_all_users,
    get_pending_payments, approve_payment, get_payment_by_id, reject_payment
)
from config import ADMIN_ID

router = Router()
logger = logging.getLogger(__name__)

# === Bir nechta adminlar uchun ruxsat ===
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", str(ADMIN_ID)).split(",") if i.strip()]

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# === /payments — Kutilayotgan to‘lovlar ro‘yxati ===
@router.message(Command("payments"))
async def payments_handler(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return await msg.answer("⛔ Sizda admin huquqi yo‘q.")

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
                InlineKeyboardButton(
                    text="📩 Bog‘lanish",
                    url=f"https://t.me/{username}" if username else f"tg://user?id={user_id}"
                )
            ]
        ])

        try:
            await msg.answer_photo(
                photo=photo_id,
                caption=(
                    f"💳 <b>To‘lov cheki</b>\n\n"
                    f"👤 {display_user}\n"
                    f"🆔 ID: <code>{user_id}</code>\n"
                    f"📎 Payment ID: <code>{payment_id}</code>\n"
                    f"🕒 Sana: {created_at}"
                ),
                parse_mode="HTML",
                reply_markup=buttons
            )
        except Exception as e:
            logger.warning(f"Rasm yuborishda xato: {e}")
            await msg.answer(
                f"💳 To‘lov: {display_user}\n📎 ID: {payment_id}",
                reply_markup=buttons
            )


# === ✅ Tasdiqlash ===
@router.callback_query(F.data.startswith("approve_"))
async def approve_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔ Siz admin emassiz.", show_alert=True)

    try:
        payment_id = int(callback.data.split("_", 1)[1])
    except:
        return await callback.answer("❌ Noto‘g‘ri ID.", show_alert=True)

    payment = get_payment_by_id(payment_id)
    if not payment:
        return await callback.answer("❌ To‘lov topilmadi yoki allaqachon ko‘rib chiqilgan.", show_alert=True)

    user_id, username = payment[1], payment[2] or "foydalanuvchi"

    approve_payment(payment_id)
    set_premium(user_id, 1)

    try:
        await callback.message.edit_caption(
            f"✅ <b>To‘lov tasdiqlandi!</b>\n👤 @{html.escape(username)}\n🆔 ID: <code>{user_id}</code>\n🎖 Premium faollashtirildi.",
            parse_mode="HTML",
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Caption yangilash xatosi: {e}")

    try:
        await callback.bot.send_message(
            user_id,
            "✅ Sizning to‘lovingiz tasdiqlandi va Premium aktivlashtirildi!\nEndi to‘liq DOCX fayllarni yuklab olishingiz mumkin 🎓"
        )
    except Exception as e:
        logger.warning(f"Foydalanuvchiga xabar yuborilmadi: {e}")

    await callback.answer("✅ Tasdiqlandi")


# === ❌ Rad etish ===
@router.callback_query(F.data.startswith("reject_"))
async def reject_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔ Siz admin emassiz.", show_alert=True)

    try:
        payment_id = int(callback.data.split("_", 1)[1])
    except:
        return await callback.answer("❌ Noto‘g‘ri ID.", show_alert=True)

    payment = get_payment_by_id(payment_id)
    if not payment:
        return await callback.answer("❌ To‘lov topilmadi.", show_alert=True)

    reject_payment(payment_id)
    user_id = payment[1]

    try:
        await callback.message.edit_caption("❌ <b>To‘lov rad etildi.</b>", parse_mode="HTML", reply_markup=None)
    except Exception as e:
        logger.error(f"edit_caption xato: {e}")

    try:
        await callback.bot.send_message(
            user_id,
            "❌ Sizning to‘lovingiz rad etildi. Agar bu xato deb o‘ylasangiz, admin bilan bog‘laning."
        )
    except Exception as e:
        logger.warning(f"Foydalanuvchiga xabar yuborilmadi: {e}")

    await callback.answer("❌ Rad etildi")


# === ⛔ Foydalanuvchini bloklash ===
@router.callback_query(F.data.startswith("block_"))
async def block_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔ Siz admin emassiz.", show_alert=True)

    try:
        user_id = int(callback.data.split("_", 1)[1])
    except:
        return await callback.answer("❌ Noto‘g‘ri user ID.", show_alert=True)

    block_user(user_id)

    try:
        await callback.message.edit_caption("⛔ <b>Foydalanuvchi bloklandi.</b>", parse_mode="HTML", reply_markup=None)
    except Exception as e:
        logger.error(f"edit_caption xato: {e}")

    try:
        await callback.bot.send_message(user_id, "⛔ Siz administrator tomonidan bloklandingiz.")
    except Exception as e:
        logger.warning(f"Bloklangan foydalanuvchiga xabar yuborilmadi: {e}")

    await callback.answer("⛔ Bloklandi")


# === 📊 Statistika ===
@router.message(Command("stats"))
async def stats_handler(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return await msg.answer("⛔ Siz admin emassiz.")
    try:
        total_users = get_users_count()
        pending = len(get_pending_payments())
        text = (
            f"📊 <b>Statistika</b>\n\n"
            f"👥 Umumiy foydalanuvchilar: <b>{total_users}</b>\n"
            f"💳 Kutilayotgan to‘lovlar: <b>{pending}</b>\n"
            f"👑 Adminlar soni: <b>{len(ADMIN_IDS)}</b>"
        )
        await msg.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Statistika olishda xatolik: {e}")
        await msg.answer("❌ Statistika olishda xatolik yuz berdi.")


# === 📢 Barcha foydalanuvchilarga xabar yuborish ===
@router.message(Command("sendall"))
async def send_all(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return await msg.answer("⛔ Siz admin emassiz.")
    args = msg.text.split(" ", 1)
    if len(args) < 2:
        return await msg.answer("❗ Foydalanish: <code>/sendall Xabar matni</code>", parse_mode="HTML")

    text = args[1]
    users = get_all_users()
    success, failed = 0, 0
    await msg.answer(f"📤 Xabar yuborish boshlandi ({len(users)} ta foydalanuvchi)...")

    for u in users:
        try:
            await msg.bot.send_message(u[0], text)
            success += 1
        except:
            failed += 1

    await msg.answer(f"✅ Yuborildi: {success}\n⚠️ Yetkazilmadi: {failed}")


# === 🟢 /premium — Foydalanuvchini Premium qilish ===
@router.message(Command("premium"))
async def make_premium(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return await msg.answer("⛔ Siz admin emassiz.")
    args = msg.text.split(" ", 1)
    if len(args) < 2:
        return await msg.answer("❗ Foydalanish: /premium <user_id> yoki @username")

    user_ref = args[1].strip().replace("@", "")
    try:
        user_id = int(user_ref)
    except:
        return await msg.answer("⚠️ Faqat user_id bilan ishlaydi (raqam bo‘lishi kerak).")

    set_premium(user_id, 1)
    await msg.answer(f"✅ Foydalanuvchi {user_id} Premium qilindi.")
    try:
        await msg.bot.send_message(user_id, "🎖 Sizga Premium berildi! Endi to‘liq hujjatlarni yuklab olishingiz mumkin.")
    except:
        pass


# === 🔓 /unblock — Blokdan chiqarish ===
@router.message(Command("unblock"))
async def unblock(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return await msg.answer("⛔ Siz admin emassiz.")
    args = msg.text.split(" ", 1)
    if len(args) < 2:
        return await msg.answer("❗ Foydalanish: /unblock <user_id>")

    try:
        user_id = int(args[1])
        unblock_user(user_id)
        await msg.answer(f"✅ Foydalanuvchi {user_id} blokdan chiqarildi.")
        await msg.bot.send_message(user_id, "✅ Sizning profilingiz blokdan chiqarildi.")
    except Exception as e:
        await msg.answer(f"❌ Xatolik: {e}")
