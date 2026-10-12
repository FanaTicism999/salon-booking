import asyncio
import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart, Command
from maxapi.types import (
    MessageCreated,
    MessageCallback,
    CallbackButton,
)
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.enums.format import Format

from app.database.engine import init_db
from app.database import requests as rq
from app import github_api
from app.handlers.booking import today_salon, now_salon, ALL_TIMES

load_dotenv()
logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("MAX_BOT_TOKEN"))
dp = Dispatcher()

# ===== Главное меню =====

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="📝 Записаться", payload="menu_book"),
    )
    builder.row(
        CallbackButton(text="📋 Мои записи", payload="menu_my_bookings"),
    )
    builder.row(
        CallbackButton(text="ℹ️ О нас", payload="menu_about"),
    )
    return builder.as_markup()

# ===== /start =====

@dp.message_created(CommandStart())
async def cmd_start(event: MessageCreated):
    user_id = event.message.sender.user_id

    # Проверка блокировки
    if await rq.is_blocked(user_id):
        await event.message.answer(
            "⛔ Вы заблокированы и не можете использовать бота."
        )
        return

    # Создаём/получаем пользователя
    sender = event.message.sender
    await rq.get_or_create_user(
        telegram_id=user_id,
        first_name=sender.first_name or sender.name or "клиент",
        username=sender.username,
    )

    await event.message.answer(
        f"Привет, {sender.first_name or sender.name or 'друг'}! 👋\n\n"
        f"Я бот для записи на услуги.\n"
        f"Выбери, что тебя интересует:",
        attachments=[main_menu()],
    )

# ===== «О нас» =====

@dp.message_callback(F.callback.payload == "menu_about")
async def cb_about(event: MessageCallback):
    try:
        data, _ = await github_api.get_site_json()
        name = data.get("salon_name", "Салон")
        address = data.get("address", "—")
        phone = data.get("phone", "—")
        bot_url = data.get("telegram_bot", "")

        text = (
            f"ℹ️ <b>{name}</b>\n\n"
            f"📍 <b>Адрес:</b> {address}\n"
            f"📞 <b>Телефон:</b> {phone}\n\n"
            f"💬 <b>Мы в Telegram:</b> {bot_url}\n\n"
            f"📝 Записаться можно прямо в этом боте."
        )
        await event.message.answer(text, format=Format.HTML)
    except Exception as e:
        await event.message.answer(
            "ℹ️ Информация о салоне временно недоступна."
        )
        print(f"Ошибка в about: {e}")

    await event.answer()

# ===== «Записаться» — список услуг =====

@dp.message_callback(F.callback.payload == "menu_book")
async def cb_book(event: MessageCallback):
    user_id = event.message.sender.user_id

    if await rq.is_blocked(user_id):
        await event.message.answer("⛔ Вы заблокированы и не можете записаться.")
        await event.answer()
        return

    services = await rq.get_all_services(only_active=True)
    if not services:
        await event.message.answer("📭 Пока услуг нет. Загляни позже!")
        await event.answer()
        return

    builder = InlineKeyboardBuilder()
    for s in services:
        builder.row(
            CallbackButton(
                text=f"{s.name} — {s.price} ₽ ({s.duration} мин)",
                payload=f"service_{s.id}",
            )
        )
    builder.row(CallbackButton(text="⬅️ Назад", payload="menu_back"))

    await event.message.answer(
        "Выбери услугу:",
        attachments=[builder.as_markup()],
    )
    await event.answer()

# ===== Назад в главное меню =====

@dp.message_callback(F.callback.payload == "menu_back")
async def cb_back(event: MessageCallback):
    await event.message.answer(
        "Выбери, что тебя интересует:",
        attachments=[main_menu()],
    )
    await event.answer()

# ===== Выбор услуги — показываем даты =====

@dp.message_callback(F.callback.payload.startswith("service_"))
async def cb_service(event: MessageCallback):
    service_id = int(event.callback.payload.split("_")[1])

    services = await rq.get_all_services(only_active=True)
    service = next((s for s in services if s.id == service_id), None)
    if service is None:
        await event.message.answer("❌ Услуга не найдена.")
        await event.answer()
        return

    today = today_salon()
    weekdays_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    builder = InlineKeyboardBuilder()
    for i in range(7):
        d = today + timedelta(days=i)
        if i == 0:
            label = f"Сегодня, {d.strftime('%d.%m')}"
        elif i == 1:
            label = f"Завтра, {d.strftime('%d.%m')}"
        else:
            label = f"{weekdays_ru[d.weekday()]}, {d.strftime('%d.%m')}"

        builder.row(
            CallbackButton(
                text=label,
                payload=f"date_{service_id}_{d.isoformat()}",
            )
        )
    builder.row(CallbackButton(text="⬅️ Назад", payload="menu_book"))

    await event.message.answer(
        f"Ты выбрал: {service.name} — {service.price} ₽\n\n📅 Выбери дату:",
        attachments=[builder.as_markup()],
    )
    await event.answer()

# ===== Выбор даты — показываем время =====

@dp.message_callback(F.callback.payload.startswith("date_"))
async def cb_date(event: MessageCallback):
    parts = event.callback.payload.split("_")
    service_id = int(parts[1])
    date_str = parts[2]

    booked = await rq.get_booked_times(date_str)

    today = today_salon()
    is_today = date_str == today.isoformat()
    now_plus_2h = now_salon() + timedelta(hours=2)

    builder = InlineKeyboardBuilder()
    free_count = 0
    row_buffer = []

    for t in ALL_TIMES:
        if t in booked:
            continue
        if is_today:
            hour, minute = map(int, t.split(":"))
            slot_time = datetime.combine(
                today,
                datetime.min.time().replace(hour=hour, minute=minute),
            )
            if slot_time <= now_plus_2h:
                continue

        row_buffer.append(
            CallbackButton(
                text=t,
                payload=f"time_{service_id}_{date_str}_{t}",
            )
        )
        free_count += 1

        if len(row_buffer) == 3:
            builder.row(*row_buffer)
            row_buffer = []

    if row_buffer:
        builder.row(*row_buffer)

    if free_count == 0:
        builder.row(
            CallbackButton(
                text="⬅️ Выбрать другую дату",
                payload=f"service_{service_id}",
            )
        )
    else:
        builder.row(
            CallbackButton(text="⬅️ Назад", payload=f"service_{service_id}")
        )

    await event.message.answer(
        f"📅 Дата: {date_str}\n\n⏰ Выбери время:",
        attachments=[builder.as_markup()],
    )
    await event.answer()

# ===== Выбор времени — сохраняем запись =====

@dp.message_callback(F.callback.payload.startswith("time_"))
async def cb_time(event: MessageCallback):
    parts = event.callback.payload.split("_")
    service_id = int(parts[1])
    date_str = parts[2]
    time_str = parts[3]

    user_id = event.message.sender.user_id

    if await rq.is_blocked(user_id):
        await event.message.answer("⛔ Вы заблокированы.")
        await event.answer()
        return

    booked = await rq.get_booked_times(date_str)
    if time_str in booked:
        await event.message.answer(
            "⚠️ Это время уже занято. Выбери другое:",
            attachments=[main_menu()],
        )
        await event.answer()
        return

    sender = event.message.sender
    user = await rq.get_or_create_user(
        telegram_id=user_id,
        first_name=sender.first_name or sender.name or "клиент",
        username=sender.username,
    )

    await rq.create_booking(
        user_id=user.id,
        service_id=service_id,
        date=date_str,
        time=time_str,
    )

    services = await rq.get_all_services(only_active=False)
    service = next((s for s in services if s.id == service_id), None)
    service_name = service.name if service else "услуга"

    await event.message.answer(
        f"✅ Ты записан!\n\n"
        f"📝 Услуга: {service_name}\n"
        f"📅 Дата: {date_str}\n"
        f"⏰ Время: {time_str}\n\n"
        f"Посмотреть записи — «📋 Мои записи».",
        attachments=[main_menu()],
    )
    await event.answer()

# ===== «Мои записи» =====

@dp.message_callback(F.callback.payload == "menu_my_bookings")
async def cb_my_bookings(event: MessageCallback):
    user_id = event.message.sender.user_id

    sender = event.message.sender
    user = await rq.get_or_create_user(
        telegram_id=user_id,
        first_name=sender.first_name or sender.name or "клиент",
        username=sender.username,
    )

    bookings = await rq.get_user_bookings(user.id)
    active = [b for b in bookings if b.status != "cancelled"]

    if not active:
        await event.message.answer(
            "📭 У тебя нет активных записей.\n\n"
            "Запишись через кнопку «📝 Записаться».",
            attachments=[main_menu()],
        )
        await event.answer()
        return

    services = await rq.get_all_services(only_active=False)
    services_map = {s.id: s for s in services}

    builder = InlineKeyboardBuilder()
    text = "📋 <b>Твои записи:</b>\n\n"

    for b in active:
        service = services_map.get(b.service_id)
        service_name = service.name if service else "услуга удалена"
        text += f"📅 {b.date} в {b.time} — {service_name}\n"
        builder.row(
            CallbackButton(
                text=f"❌ Отменить {b.date} {b.time}",
                payload=f"cancel_{b.id}",
            )
        )

    builder.row(CallbackButton(text="⬅️ Назад", payload="menu_back"))

    await event.message.answer(
        text,
        format=Format.HTML,
        attachments=[builder.as_markup()],
    )
    await event.answer()

# ===== Отмена записи =====

@dp.message_callback(F.callback.payload.startswith("cancel_"))
async def cb_cancel(event: MessageCallback):
    booking_id = int(event.callback.payload.split("_")[1])

    booking = await rq.get_booking_by_id(booking_id)
    if booking is None:
        await event.message.answer("❌ Запись не найдена.")
        await event.answer()
        return

    user_id = event.message.sender.user_id
    sender = event.message.sender
    user = await rq.get_or_create_user(
        telegram_id=user_id,
        first_name=sender.first_name or sender.name or "клиент",
        username=sender.username,
    )

    if booking.user_id != user.id:
        await event.message.answer("⛔ Это не твоя запись.")
        await event.answer()
        return

    await rq.cancel_booking(booking_id)

    await event.message.answer(
        f"✅ Запись на {booking.date} в {booking.time} отменена.",
        attachments=[main_menu()],
    )
    await event.answer()

# ===== Эхо (для отладки) =====

@dp.message_created(F.message.body.text)
async def echo(event: MessageCreated):
    await event.message.answer(f"Эхо: {event.message.body.text}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())