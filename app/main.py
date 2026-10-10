import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiohttp import web

from app.database.engine import init_db
from app.handlers import admin, client, booking, editor, uploads, help_cmd

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ===== Заглушка для Render (чтобы он видел открытый порт) =====

async def health_check(request):
    return web.Response(text="OK")


async def run_fake_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Health check server started on port {port}")


# ===== Запуск бота =====

async def main():
    await init_db()
    print("База данных готова!")

    await run_fake_server()

    # Подключаем роутеры (ВНУТРИ main!)
    dp.include_router(admin.router)
    dp.include_router(editor.router)
    dp.include_router(uploads.router)
    dp.include_router(help_cmd.router)
    dp.include_router(booking.router)      # booking ДО client
    dp.include_router(client.router)

    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())