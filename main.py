# main.py
import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.user import router as user_router
from handlers.admin import router as admin_router
from handlers.payment import router as payment_router
from utils.db import init_db
async def main():
    print("Bot ishga tushdi!")  # Log
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    init_db()

    # Routers
    dp.include_router(user_router)
    dp.include_router(admin_router)
    dp.include_router(payment_router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

