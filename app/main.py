import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from app.database.engine import init_db
from app.handlers import admin, client, booking, editor

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def main():
    await init_db()
    print("База данных готова!")

    dp.include_router(admin.router)
    dp.include_router(client.router)
    dp.include_router(booking.router)
    dp.include_router(editor.router)   

    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

    