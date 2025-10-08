# handlers/admin.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import html, logging, asyncio
from utils.db import (
    set_premium, block_user, unblock_user, is_blocked, get_users_count,
    get_pending_payments, approve_payment, get_payment_by_id, reject_payment,
)
from config import ADMIN_ID

router = Router()
logger = logging.getLogger(__name__)

# === ADMIN TEKSHIRISH ===
def is_admin(msg: types.Message) -> bool:
    return msg.from_user.id == ADMIN_ID


# === ADMIN MENYUSI ===
def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💳 To‘lovlar"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="⛔ Bloklash"), KeyboardButton(text="✅ Blokdan chiqarish")],
            [KeyboardButton(text="📢 Xabar yuborish")],
            [KeyboardButton(text="🏠 Asosiy menyu")]
        ],
        resize_keyboard=True
    )


# === /admin BUYRUG‘I ===
@router.message(Command("admin"))
async def admin_panel(msg: types.Message):
    if not is_admin(msg):
        return await msg.answer("⛔ Siz admin emassiz.")
    await msg.answer("🔐 Admin paneliga xush kelibsiz!", reply_markup=admin_menu())


# === TO‘LOVLARNI KO‘RISH ===
@router.message(F.text.in_(["💳 To‘lovlar", "/payments"]))
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
            await msg.answer(f"📎 Payment ID: {payment_id} — @{username}", reply_markup=buttons)


# === STATISTIKA ===
@router.message(F.text == "📊 Statistika")
async def stats_handler(msg: types.Message):
    if not is_admin(msg): return
    from utils.db import connect
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE premium=1")
    premium = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE blocked=1")
    blocked = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]
    conn.close()

    text = (
        "📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Umumiy foydalanuvchilar: <b>{total}</b>\n"
        f"🎖 Premium: <b>{premium}</b>\n"
        f"⛔ Bloklangan: <b>{blocked}</b>"
    )
    await msg.answer(text, parse_mode="HTML")


# === FOYDALANUVCHINI BLOKLASH ===
@router.message(F.text == "⛔ Bloklash")
async def ask_block(msg: types.Message):
    if not is_admin(msg): return
    await msg.answer("Bloklanadigan foydalanuvchi ID raqamini kiriting:")
    from utils.db import set_state
    set_state(ADMIN_ID, "admin_block_user")

@router.message(F.text.regexp(r"^\d+$"))
async def block_user_by_id(msg: types.Message):
    from utils.db import get_state, set_state
    if not is_admin(msg): return
    state = get_state(ADMIN_ID)
    if state == "admin_block_user":
        user_id = int(msg.text)
        block_user(user_id)
        set_state(ADMIN_ID, None)
        await msg.answer(f"⛔ Foydalanuvchi {user_id} bloklandi.")
        try:
            await msg.bot.send_message(user_id, "⛔ Siz administrator tomonidan bloklandingiz.")
        except:
            pass


# === FOYDALANUVCHINI BLOKDAN CHIQARISH ===
@router.message(F.text == "✅ Blokdan chiqarish")
async def ask_unblock(msg: types.Message):
    if not is_admin(msg): return
    await msg.answer("Blokdan chiqariladigan foydalanuvchi ID raqamini kiriting:")
    from utils.db import set_state
    set_state(ADMIN_ID, "admin_unblock_user")

@router.message(F.text.regexp(r"^\d+$"))
async def unblock_user_by_id(msg: types.Message):
    from utils.db import get_state, set_state
    if not is_admin(msg): return
    state = get_state(ADMIN_ID)
    if state == "admin_unblock_user":
        user_id = int(msg.text)
        unblock_user(user_id)
        set_state(ADMIN_ID, None)
        await msg.answer(f"✅ Foydalanuvchi {user_id} blokdan chiqarildi.")
        try:
            await msg.bot.send_message(user_id, "✅ Siz blokdan chiqarildingiz, endi botdan foydalanishingiz mumkin.")
        except:
            pass


# === BROADCAST FUNKSIYASI ===
@router.message(F.text == "📢 Xabar yuborish")
async def start_broadcast(msg: types.Message):
    if not is_admin(msg): return
    from utils.db import set_state
    set_state(ADMIN_ID, "admin_broadcast")
    await msg.answer("📢 Yuboriladigan xabar matnini kiriting:")


@router.message()
async def broadcast_handler(msg: types.Message):
    from utils.db import get_state, set_state, connect
    if not is_admin(msg): return
    state = get_state(ADMIN_ID)
    if state == "admin_broadcast":
        text = msg.text
        conn = connect()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE blocked=0")
        users = cur.fetchall()
        conn.close()
        set_state(ADMIN_ID, None)
        await msg.answer(f"📨 Xabar {len(users)} ta foydalanuvchiga yuborilmoqda...")

        sent, failed = 0, 0
        for (uid,) in users:
            try:
                await msg.bot.send_message(uid, text)
                sent += 1
                await asyncio.sleep(0.05)
            except:
                failed += 1

        await msg.answer(f"✅ Yuborildi: {sent}\n❌ Yetkazilmadi: {failed}")


# === CALLBACKLAR (to‘lovlar) ===
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
        return await callback.answer("❌ To‘lov topilmadi.", show_alert=True)

    if payment[4] == 1:
        return await callback.answer("❌ Bu to‘lov allaqachon tasdiqlangan.", show_alert=True)

    user_id = payment[1]
    username = payment[2] or ""

    approve_payment(payment_id)
    set_premium(user_id, 1)

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

    try:
        await callback.message.bot.send_message(
            user_id,
            "✅ To‘lovingiz tasdiqlandi! Endi to‘liq .docx fayllarni yuklab olishingiz mumkin."
        )
    except Exception as e:
        logger.exception("Foydalanuvchiga xabar yuborishda xato: %s", e)

    await callback.answer("✅ Tasdiqlandi")
