import asyncio
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiohttp import web

# Загружаем .env ДО импорта модулей app.*
load_dotenv()

from app.database.engine import init_db
from app.handlers import admin, client, booking, editor, uploads, help_cmd

# Max-бот — импортируем модуль, используем его bot и dp
from app.max_handlers import client_max as max_client


# ===== Telegram-бот =====

BOT_TOKEN = os.getenv("BOT_TOKEN")
tg_bot = Bot(token=BOT_TOKEN)
tg_dp = Dispatcher()


# ===== Health check для Render =====

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


# ===== Запуск Telegram-бота =====

async def run_telegram():
    tg_dp.include_router(admin.router)
    tg_dp.include_router(editor.router)
    tg_dp.include_router(uploads.router)
    tg_dp.include_router(help_cmd.router)
    tg_dp.include_router(booking.router)
    tg_dp.include_router(client.router)

    print("Telegram-бот запущен!")
    await tg_dp.start_polling(tg_bot)


# ===== Запуск Max-бота =====

async def run_max():
    print("Max-бот запущен!")
    await max_client.dp.start_polling(max_client.bot)


# ===== Главная =====

async def main():
    await init_db()
    print("База данных готова!")

    await run_fake_server()

    # Запускаем оба бота параллельно
    await asyncio.gather(
        run_telegram(),
        run_max(),
    )


if __name__ == "__main__":
    asyncio.run(main())