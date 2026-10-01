import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from app.database.engine import init_db
from app.handlers import admin, client, booking, editor, uploads

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== Заглушка для Render (чтобы он видел открытый порт) =====
from aiohttp import web

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

async def main():
    await init_db()
    print("База данных готова!")

    await run_fake_server()

    dp.include_router(admin.router)
    dp.include_router(editor.router)     
    dp.include_router(uploads.router)
    dp.include_router(client.router)
    dp.include_router(booking.router)

    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

    