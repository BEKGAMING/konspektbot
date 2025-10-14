# handlers/admin.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import html, logging
from utils.db import (
    set_premium, block_user, unblock_user, get_users_count,
    get_pending_payments, approve_payment, get_payment_by_id,
    reject_payment, get_free_uses, get_blocked_users, get_all_users
)
from config import ADMIN_ID

router = Router()
logger = logging.getLogger(__name__)

def is_admin(msg: types.Message) -> bool:
    return msg.from_user.id == ADMIN_ID


# === ADMIN PANEL ===
@router.message(Command("admin"))
async def admin_panel(msg: types.Message):
    if not is_admin(msg):
        return await msg.answer("⛔ Siz admin emassiz.")

    adminbuttons = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📊 Statistika"), types.KeyboardButton(text="💳 To‘lovlar")],
            [types.KeyboardButton(text="👥 Foydalanuvchilar"), types.KeyboardButton(text="🚫 Bloklanganlar")],
            [types.KeyboardButton(text="🔓 Blokdan chiqarish"), types.KeyboardButton(text="⬅️ Asosiy menyu")]
        ],
        resize_keyboard=True
    )
    await msg.answer("👑 Admin paneliga xush kelibsiz!", reply_markup=adminbuttons)


# === 📊 Statistika ===
@router.message(F.text == "📊 Statistika")
async def show_stats(msg: types.Message):
    if not is_admin(msg):
        return await msg.answer("⛔ Siz admin emassiz.")
    total_users = get_users_count()
    blocked = len(get_blocked_users())
    await msg.answer(
        f"📈 <b>Statistika:</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{total_users}</b>\n"
        f"🚫 Bloklanganlar: <b>{blocked}</b>",
        parse_mode="HTML"
    )


# === 💳 To‘lovlarni ko‘rish ===
@router.message(F.text == "💳 To‘lovlar")
async def payments_handler(msg: types.Message):
    if not is_admin(msg):
        return await msg.answer("⛔ Siz admin emassiz.")

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
        except Exception as e:
            await msg.answer(f"📎 Payment ID: {payment_id} — @{username}", reply_markup=buttons)
            logger.error(e)


# === ✅ Tasdiqlash ===
@router.callback_query(F.data.startswith("approve_"))
async def approve_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔ Siz admin emassiz.", show_alert=True)

    payment_id = int(callback.data.split("_", 1)[1])
    payment = get_payment_by_id(payment_id)
    if not payment:
        return await callback.answer("❌ To‘lov topilmadi.", show_alert=True)

    if payment[4] == 1:
        return await callback.answer("❌ Bu to‘lov allaqachon tasdiqlangan.", show_alert=True)

    user_id = payment[1]
    username = payment[2] or "foydalanuvchi"

    approve_payment(payment_id)
    set_premium(user_id, 1)

    # agar 3 martalik limit tugagan bo‘lsa — nolga tushuramiz
    if get_free_uses(user_id) >= 3:
        from utils.db import connect
        conn = connect()
        cur = conn.cursor()
        cur.execute("UPDATE users SET free_uses = 0 WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()

    await callback.message.edit_caption(
        f"✅ <b>To‘lov tasdiqlandi!</b>\n\n"
        f"👤 @{html.escape(username)}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🎖 Premium faollashtirildi.",
        parse_mode="HTML"
    )

    try:
        await callback.message.bot.send_message(
            user_id,
            "🎉 <b>Tabriklaymiz!</b>\n"
            "✅ Sizning to‘lovingiz tasdiqlandi va Premium faollashtirildi.\n\n"
            "Endi siz cheklovsiz barcha xizmatlardan foydalanishingiz mumkin.",
            parse_mode="HTML"
        )
    except:
        pass

    await callback.answer("✅ Tasdiqlandi!")


# === ❌ Rad etish ===
@router.callback_query(F.data.startswith("reject_"))
async def reject_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔ Siz admin emassiz.", show_alert=True)

    payment_id = int(callback.data.split("_", 1)[1])
    payment = get_payment_by_id(payment_id)
    if not payment:
        return await callback.answer("❌ To‘lov topilmadi.", show_alert=True)

    reject_payment(payment_id)

    await callback.message.edit_caption("❌ <b>Rad etildi.</b> Admin tomonidan rad etildi.", parse_mode="HTML")

    try:
        await callback.message.bot.send_message(
            payment[1],
            "❌ Sizning to‘lovingiz rad etildi.\n"
            "Iltimos, to‘lovni qayta yuboring yoki admin bilan bog‘laning."
        )
    except:
        pass

    await callback.answer("❌ Rad etildi.")


# === ⛔ Bloklash ===
@router.callback_query(F.data.startswith("block_"))
async def block_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔ Siz admin emassiz.", show_alert=True)
    user_id = int(callback.data.split("_", 1)[1])
    block_user(user_id)
    await callback.message.edit_caption("⛔ <b>Foydalanuvchi bloklandi.</b>", parse_mode="HTML")
    try:
        await callback.message.bot.send_message(user_id, "⛔ Siz administrator tomonidan bloklandingiz.")
    except:
        pass
    await callback.answer("⛔ Bloklandi.")


# === 🔓 Blokdan chiqarish ===
@router.message(F.text == "🔓 Blokdan chiqarish")
async def unblock_command(msg: types.Message):
    if not is_admin(msg):
        return await msg.answer("⛔ Siz admin emassiz.")
    blocked_users = get_blocked_users()
    if not blocked_users:
        return await msg.answer("✅ Bloklangan foydalanuvchilar yo‘q.")
    text = "🚫 <b>Bloklangan foydalanuvchilar:</b>\n\n"
    for u in blocked_users:
        text += f"🆔 {u[0]} — @{u[1] or 'username yo‘q'}\n"
    text += "\nFoydalanuvchini ID orqali unbloklash uchun /unblock [id] yozing."
    await msg.answer(text, parse_mode="HTML")


# === /unblock [id] ===
@router.message(Command("unblock"))
async def unblock_cmd(msg: types.Message):
    if not is_admin(msg):
        return await msg.answer("⛔ Siz admin emassiz.")
    parts = msg.text.strip().split()
    if len(parts) < 2:
        return await msg.answer("🔧 Foydalanuvchini unbloklash uchun ID yuboring.\nMasalan: /unblock 123456789")
    user_id = int(parts[1])
    unblock_user(user_id)
    await msg.answer(f"✅ Foydalanuvchi ({user_id}) qayta faollashtirildi.")
    try:
        await msg.bot.send_message(user_id, "✅ Sizning profilingiz yana faollashtirildi.")
    except:
        pass
