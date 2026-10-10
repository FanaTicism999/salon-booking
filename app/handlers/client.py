from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
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
async def cb_select_service(callback: types.CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[1])
    from app.handlers.booking import start_booking
    await start_booking(callback, state, service_id)

# ===== Кнопка "Мои записи" =====

@router.callback_query(F.data == "my_bookings")
async def cb_my_bookings(callback: types.CallbackQuery):
    await show_my_bookings(callback.message, callback.from_user.id)
    await callback.answer()


# Команда /my_bookings
@router.message(Command("my_bookings"))
async def cmd_my_bookings(message: types.Message):
    await show_my_bookings(message, message.from_user.id)


async def show_my_bookings(message: types.Message, telegram_id: int):
    """Показывает все активные записи клиента."""
    user = await rq.get_or_create_user(
        telegram_id=telegram_id,
        first_name=message.chat.first_name or "клиент",
        username=message.chat.username,
    )

    bookings = await rq.get_user_bookings(user.id)
    active = [b for b in bookings if b.status != "cancelled"]

    if not active:
        await message.answer(
            "📭 У тебя нет активных записей.\n\n"
            "Запишись через кнопку «📝 Записаться»."
        )
        return

    # Получаем названия услуг
    services = await rq.get_all_services(only_active=False)
    services_map = {s.id: s for s in services}

    builder = InlineKeyboardBuilder()
    text = "📋 Твои записи:\n\n"

    for b in active:
        service = services_map.get(b.service_id)
        service_name = service.name if service else "услуга удалена"
        text += f"📅 {b.date} в {b.time} — {service_name}\n"
        builder.button(
            text=f"❌ Отменить {b.date} {b.time}",
            callback_data=f"cancel_{b.id}"
        )

    builder.adjust(1)
    await message.answer(text, reply_markup=builder.as_markup())


# ===== Отмена записи =====

@router.callback_query(F.data.regexp(r"^cancel_\d+$"))
async def cb_cancel_booking(callback: types.CallbackQuery):
    booking_id = int(callback.data.split("_")[1])

    # Проверяем, что запись принадлежит этому пользователю
    booking = await rq.get_booking_by_id(booking_id)
    if booking is None:
        await callback.message.answer("❌ Запись не найдена.")
        await callback.answer()
        return

    user = await rq.get_or_create_user(
        telegram_id=callback.from_user.id,
        first_name=callback.from_user.first_name,
        username=callback.from_user.username,
    )

    if booking.user_id != user.id:
        await callback.message.answer("⛔ Это не твоя запись.")
        await callback.answer()
        return

    await rq.cancel_booking(booking_id)
    await callback.message.answer(
        f"✅ Запись на {booking.date} в {booking.time} отменена."
    )
    await callback.answer()

# ===== Прочие сообщения =====

@router.message()
async def echo(message: types.Message):
    await message.answer(f"Ты написал: {message.text}")

@router.callback_query(F.data == "about")
async def cb_about(callback: types.CallbackQuery):
    from app import github_api

    try:
        # Читаем данные сайта из GitHub
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
            f"📝 Записаться можно прямо в этом боте — нажми «📝 Записаться»."
        )

        await callback.message.answer(text, parse_mode="HTML")
    except Exception as e:
        await callback.message.answer(
            "ℹ️ Информация о салоне временно недоступна.\n"
            f"Попробуйте позже. 🚧"
        )
        print(f"Ошибка в /about: {e}")

    await callback.answer()