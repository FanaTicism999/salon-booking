from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database import requests as rq

router = Router()


# ===== Главное меню =====

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Записаться", callback_data="book")
    builder.button(text="📋 Мои записи", callback_data="my_bookings")
    builder.button(text="ℹ️ О нас", callback_data="about")
    builder.adjust(1)
    return builder.as_markup()


# /start
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await rq.get_or_create_user(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username,
    )
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        f"Я бот для записи на услуги.\n"
        f"Выбери, что тебя интересует:",
        reply_markup=main_menu()
    )


# ===== Кнопка "Записаться" — показываем список услуг =====

@router.callback_query(F.data == "book")
async def cb_book(callback: types.CallbackQuery):
    services = await rq.get_all_services(only_active=True)

    if not services:
        await callback.message.answer("📭 Пока услуг нет. Загляни позже!")
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for s in services:
        builder.button(
            text=f"{s.name} — {s.price} ₽ ({s.duration} мин)",
            callback_data=f"service_{s.id}"
        )
    builder.adjust(1)

    await callback.message.answer(
        "Выбери услугу:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


# ===== Клиент выбрал услугу =====

@router.callback_query(F.data.startswith("service_"))
async def cb_select_service(callback: types.CallbackQuery):
    service_id = int(callback.data.split("_")[1])
    services = await rq.get_all_services(only_active=True)
    service = next((s for s in services if s.id == service_id), None)

    if service is None:
        await callback.message.answer("❌ Услуга не найдена.")
        await callback.answer()
        return

    await callback.message.answer(
        f"Ты выбрал: {service.name}\n"
        f"💰 Цена: {service.price} ₽\n"
        f"⏱ Длительность: {service.duration} мин\n\n"
        f"Выбор даты и времени — в следующем обновлении 🚧"
    )
    await callback.answer()


# ===== Кнопка "Мои записи" =====

@router.callback_query(F.data == "my_bookings")
async def cb_my_bookings(callback: types.CallbackQuery):
    await callback.message.answer("Здесь будут твои записи. 🚧")
    await callback.answer()


# ===== Кнопка "О нас" =====

@router.callback_query(F.data == "about")
async def cb_about(callback: types.CallbackQuery):
    await callback.message.answer(
        "Это учебный проект — система онлайн-записи.\n"
        "Скоро здесь появится информация о салоне. 🚧"
    )
    await callback.answer()


# ===== Прочие сообщения =====

@router.message()
async def echo(message: types.Message):
    await message.answer(f"Ты написал: {message.text}")