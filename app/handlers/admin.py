import os
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.database import requests as rq
from app.handlers.booking import today_salon

router = Router()

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ===== Состояния для добавления услуги =====

class AddService(StatesGroup):
    name = State()
    price = State()
    duration = State()


# ===== Команда /add_service =====

@router.message(Command("add_service"))
async def cmd_add_service(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    await message.answer("📝 Введи название услуги (например, «Стрижка»):")
    await state.set_state(AddService.name)


@router.message(AddService.name)
async def add_service_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("💰 Введи цену в рублях (только число, например «1500»):")
    await state.set_state(AddService.price)


@router.message(AddService.price)
async def add_service_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Нужно число. Попробуй ещё раз:")
        return
    await state.update_data(price=int(message.text))
    await message.answer("⏱ Введи длительность в минутах (например, «60»):")
    await state.set_state(AddService.duration)


@router.message(AddService.duration)
async def add_service_duration(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Нужно число. Попробуй ещё раз:")
        return

    data = await state.get_data()
    service = await rq.add_service(
        name=data["name"],
        price=data["price"],
        duration=int(message.text),
    )

    await message.answer(
        f"✅ Услуга добавлена!\n\n"
        f"🆔 ID: {service.id}\n"
        f"📝 Название: {service.name}\n"
        f"💰 Цена: {service.price} ₽\n"
        f"⏱ Длительность: {service.duration} мин"
    )
    await state.clear()


# ===== Команда /list_services =====

@router.message(Command("list_services"))
async def cmd_list_services(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    services = await rq.get_all_services(only_active=False)

    if not services:
        await message.answer("📭 Список услуг пуст. Добавь через /add_service")
        return

    text = "📋 Список услуг:\n\n"
    for s in services:
        status = "✅" if s.is_active else "❌"
        text += f"{status} ID {s.id}: {s.name} — {s.price} ₽ ({s.duration} мин)\n"

    await message.answer(text)


# ===== Команда /del_service =====

@router.message(Command("del_service"))
async def cmd_del_service(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /del_service ID\nНапример: /del_service 3")
        return

    ok = await rq.delete_service(int(parts[1]))
    if ok:
        await message.answer(f"✅ Услуга с ID {parts[1]} удалена.")
    else:
        await message.answer(f"❌ Услуга с ID {parts[1]} не найдена.")

        # ===== Блокировка клиентов =====

@router.message(Command("block"))
async def cmd_block(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer(
            "Использование: /block <telegram_id>\n"
            "Например: /block 123456789\n\n"
            "Найти ID клиента: /bookings_today"
        )
        return

    telegram_id = int(parts[1])
    reason = parts[2] if len(parts) > 2 else None

    added = await rq.block_user(telegram_id, reason)
    if added:
        await message.answer(
            f"✅ Клиент <code>{telegram_id}</code> заблокирован.\n"
            f"Причина: {reason or '—'}",
            parse_mode="HTML"
        )
    else:
        await message.answer(f"ℹ️ Клиент <code>{telegram_id}</code> уже заблокирован.", parse_mode="HTML")


@router.message(Command("unblock"))
async def cmd_unblock(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /unblock <telegram_id>")
        return

    telegram_id = int(parts[1])
    removed = await rq.unblock_user(telegram_id)
    if removed:
        await message.answer(f"✅ Клиент <code>{telegram_id}</code> разблокирован.", parse_mode="HTML")
    else:
        await message.answer(f"ℹ️ Клиент <code>{telegram_id}</code> не был заблокирован.", parse_mode="HTML")


@router.message(Command("blocked"))
async def cmd_blocked(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    blocked = await rq.get_blocked_users()
    if not blocked:
        await message.answer("📭 Список заблокированных пуст.")
        return

    text = f"🚫 <b>Заблокированные ({len(blocked)})</b>\n\n"
    for b in blocked:
        text += f"🆔 <code>{b.telegram_id}</code>"
        if b.reason:
            text += f" — {b.reason}"
        text += f"\n📅 {b.blocked_at.strftime('%d.%m.%Y %H:%M')}\n\n"

    await message.answer(text, parse_mode="HTML")


# ===== Записи на сегодня =====


@router.message(Command("bookings_today"))
async def cmd_bookings_today(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    today = today_salon().isoformat()
    bookings = await rq.get_bookings_for_date(today)

    if not bookings:
        await message.answer(f"📭 На сегодня ({today}) записей нет.")
        return

    services = await rq.get_all_services(only_active=False)
    services_map = {s.id: s for s in services}

    text = f"📋 <b>Записи на сегодня ({today})</b>\n\n"

    for b in bookings:
        # Получаем пользователя
        user = await rq.get_user_by_id(b.user_id)
        service = services_map.get(b.service_id)
        service_name = service.name if service else "услуга удалена"

        text += f"🕐 <b>{b.time}</b> — {service_name}\n"
        if user:
            text += f"👤 {user.first_name}"
            if user.username:
                text += f" (@{user.username})"
            text += f"\n🆔 <code>{user.telegram_id}</code>\n"
        text += f"📅 {b.date}\n\n"

    text += f"<b>Всего: {len(bookings)}</b>"
    await message.answer(text, parse_mode="HTML")