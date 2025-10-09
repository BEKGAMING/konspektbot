# main.py
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiohttp import web
from config import BOT_TOKEN
from handlers.user import router as user_router
from handlers.admin import router as admin_router  # admin router import
from handlers.payment import router as payment_router
from utils.db import init_db

WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL")  # Render avtomatik URL beradi
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else None

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(user_router)
dp.include_router(admin_router)  # admin routerni ulaymiz
dp.include_router(payment_router)
init_db()


async def on_startup(app):
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
        print(f"Webhook set to: {WEBHOOK_URL}")
    else:
        print("⚠️ WEBHOOK_URL mavjud emas!")


async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()


async def handle_webhook(request):
    update = types.Update(**await request.json())
    await dp.feed_update(bot, update)
    return web.Response(text="ok")


async def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    port = int(os.getenv("PORT", 8080))
    print(f"🌐 Server running on port {port}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
