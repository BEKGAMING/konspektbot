# main.py
import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from config import BOT_TOKEN
from handlers.user import router as user_router
from handlers.admin import router as admin_router
from utils.db import init_db

# === Database init ===
init_db()

# === Webhook sozlamalari ===
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL")  # Render avtomatik URL beradi
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else None

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Routerlarni ulaymiz ===
dp.include_router(user_router)
dp.include_router(admin_router)
dp.include_router(payment_router)  # Agar alohida payment.py bo‘lsa, shu qatorni aktivlashtiring

# === Webhook startup ===
async def on_startup(app):
    if WEBHOOK_URL:
        try:
            await bot.set_webhook(WEBHOOK_URL)
            print(f"✅ Webhook o‘rnatildi: {WEBHOOK_URL}")
        except Exception as e:
            print(f"⚠️ Webhook o‘rnatishda xato: {e}")
    else:
        print("⚠️ WEBHOOK_URL mavjud emas! Render URL topilmadi.")

# === Webhook shutdown ===
async def on_shutdown(app):
    try:
        await bot.delete_webhook()
        await bot.session.close()
        print("🛑 Webhook o‘chirildi va sessiya yopildi.")
    except Exception as e:
        print(f"⚠️ Yopilishda xato: {e}")

# === Update handler ===
async def handle_webhook(request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
    except Exception as e:
        print(f"⚠️ Update qayta ishlashda xato: {e}")
    return web.Response(text="ok")

# === Asosiy server ===
async def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    port = int(os.getenv("PORT", 8080))
    print(f"🌐 Server {port}-portda ishga tushmoqda...")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print("🤖 Bot ishlayapti! Webhook mode aktiv.")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot to‘xtatildi.")
