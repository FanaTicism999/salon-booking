import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database.engine import init_db

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Клавиатура главного меню
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Записаться", callback_data="book")
    builder.button(text="📋 Мои записи", callback_data="my_bookings")
    builder.button(text="ℹ️ О нас", callback_data="about")
    builder.adjust(1)  # кнопки в столбик
    return builder.as_markup()


# /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        f"Я бот для записи на услуги.\n"
        f"Выбери, что тебя интересует:",
        reply_markup=main_menu()
    )


# Кнопка "Записаться"
@dp.callback_query(F.data == "book")
async def cb_book(callback: types.CallbackQuery):
    await callback.message.answer("Здесь скоро будет запись на услугу. 🚧")
    await callback.answer()


# Кнопка "Мои записи"
@dp.callback_query(F.data == "my_bookings")
async def cb_my_bookings(callback: types.CallbackQuery):
    await callback.message.answer("Здесь будут твои записи. 🚧")
    await callback.answer()


# Кнопка "О нас"
@dp.callback_query(F.data == "about")
async def cb_about(callback: types.CallbackQuery):
    await callback.message.answer(
        "Это учебный проект — система онлайн-записи.\n"
        "Скоро здесь появится информация о салоне. 🚧"
    )
    await callback.answer()


# Обработка прочих сообщений
@dp.message()
async def echo(message: types.Message):
    await message.answer(f"Ты написал: {message.text}")


async def main():
    await init_db()
    print("База данных готова!")
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())