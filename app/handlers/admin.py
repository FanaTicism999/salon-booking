import os
import re
from datetime import timedelta, datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database import requests as rq
from app.handlers.booking import today_salon, now_salon, ALL_TIMES

router = Router()

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ===== Состояния для добавления услуги =====

class AddService(StatesGroup):
    name = State()
    price = State()
    duration = State()


# ===== Состояния для ручной записи (по звонку) =====

class ManualBooking(StatesGroup):
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    entering_phone = State()
    entering_name = State()


# ===== Вспомогательная: пометка источника =====

def _source_icon(source: str) -> str:
    """Возвращает эмодзи для источника записи."""
    if source == "phone":
        return "📞"
    elif source == "bot":
        return "🤖"
    return "•"


# ===== Универсальная клавиатура отмены =====

def cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить создание", callback_data="mb_cancel")
    builder.adjust(1)
    return builder.as_markup()


# =========================================================================
#                              УСЛУГИ
# =========================================================================

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


# =========================================================================
#                        РУЧНАЯ ЗАПИСЬ (по звонку)
# =========================================================================

@router.message(Command("add_booking"))
async def cmd_add_booking(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    services = await rq.get_all_services(only_active=True)
    if not services:
        await message.answer("📭 Список услуг пуст. Добавь через /add_service")
        return

    builder = InlineKeyboardBuilder()
    for s in services:
        builder.button(
            text=f"{s.name} — {s.price} ₽ ({s.duration} мин)",
            callback_data=f"mb_srv_{s.id}",
        )
    builder.row(types.InlineKeyboardButton(text="❌ Отмена", callback_data="mb_cancel"))
    builder.adjust(1)

    await state.set_state(ManualBooking.choosing_service)

    await message.answer(
        "📞 <b>Создание записи по звонку</b>\n\n"
        "<b>Шаг 1/5.</b> Выбери услугу:",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("mb_srv_"), ManualBooking.choosing_service)
async def mb_choose_service(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    service_id = int(callback.data.split("_")[2])
    services = await rq.get_all_services(only_active=True)
    service = next((s for s in services if s.id == service_id), None)

    if service is None:
        await callback.message.answer("❌ Услуга не найдена.")
        await callback.answer()
        return

    await state.update_data(service_id=service_id, service_name=service.name)
    await state.set_state(ManualBooking.choosing_date)

    # Клавиатура с датами
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
        builder.button(
            text=label,
            callback_data=f"mb_date_{d.isoformat()}",
        )
    builder.row(types.InlineKeyboardButton(text="❌ Отмена", callback_data="mb_cancel"))
    builder.adjust(1)

    await callback.message.answer(
        f"Услуга: <b>{service.name}</b>\n\n"
        f"<b>Шаг 2/5.</b> Выбери дату:",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mb_date_"), ManualBooking.choosing_date)
async def mb_choose_date(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    date_str = callback.data.split("_", 2)[2]

    # Проверяем слоты
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
            types.InlineKeyboardButton(
                text=t,
                callback_data=f"mb_time_{date_str}_{t}",
            )
        )
        free_count += 1

        if len(row_buffer) == 3:
            builder.row(*row_buffer)
            row_buffer = []

    if row_buffer:
        builder.row(*row_buffer)

    builder.row(types.InlineKeyboardButton(text="❌ Отмена", callback_data="mb_cancel"))
    builder.adjust(3)

    if free_count == 0:
        await callback.message.answer(
            f"📅 Дата: {date_str}\n\n"
            f"⚠️ На эту дату нет свободных слотов.",
            reply_markup=cancel_kb(),
        )
    else:
        await callback.message.answer(
            f"📅 Дата: <b>{date_str}</b>\n\n"
            f"<b>Шаг 3/5.</b> Выбери время:",
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("mb_time_"), ManualBooking.choosing_time)
async def mb_choose_time(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    # Формат: mb_time_<date>_<time>
    # Разбиваем по "_" но date содержит дефисы, а time содержит ":" — оба безопасны
    parts = callback.data.split("_")
    # parts[0]=mb, parts[1]=time, parts[2]=date, parts[3]=time
    date_str = parts[2]
    time_str = parts[3]

    # Проверяем занятость
    booked = await rq.get_booked_times(date_str)
    if time_str in booked:
        await callback.message.answer(
            "⚠️ Это время уже занято. Выбери другое.",
            reply_markup=cancel_kb(),
        )
        await callback.answer()
        return

    await state.update_data(date_str=date_str, time_str=time_str)
    await state.set_state(ManualBooking.entering_phone)

    await callback.message.answer(
        f"⏰ Время: <b>{time_str}</b>\n\n"
        f"<b>Шаг 4/5.</b> Введи телефон клиента:\n"
        f"Формат: <code>+7XXXXXXXXXX</code>\n"
        f"Например: <code>+79178074943</code>",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(ManualBooking.entering_phone)
async def mb_enter_phone(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    phone_raw = (message.text or "").strip()
    digits = "".join(c for c in phone_raw if c.isdigit() or c == "+")

    # Нормализация
    if digits.startswith("8") and len(digits) == 11:
        digits = "+7" + digits[1:]
    elif digits.startswith("7") and len(digits) == 11:
        digits = "+" + digits
    elif digits.startswith("+7") and len(digits) == 12:
        pass
    else:
        await message.answer(
            "⚠️ Неверный формат. Нужно 11 цифр, начиная с +7.\n"
            "Пример: <code>+79178074943</code>",
            parse_mode="HTML",
        )
        return

    await state.update_data(phone=digits)
    await state.set_state(ManualBooking.entering_name)

    await message.answer(
        f"📱 Телефон: <b>{digits}</b>\n\n"
        f"<b>Шаг 5/5.</b> Введи имя клиента:\n"
        f"(или отправь <code>-</code> — сохраним как «Клиент»)",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(ManualBooking.entering_name)
async def mb_enter_name(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    name_raw = (message.text or "").strip()
    if name_raw in ("", "-", "—"):
        name = "Клиент"
    else:
        name = name_raw

    data = await state.get_data()
    service_id = data.get("service_id")
    service_name = data.get("service_name", "услуга")
    date_str = data.get("date_str")
    time_str = data.get("time_str")
    phone = data.get("phone")

    # Создаём виртуального пользователя
    virtual_user = await rq.create_virtual_user(
        first_name=name,
        phone=phone,
    )

    # Создаём запись
    await rq.create_booking(
        user_id=virtual_user.id,
        service_id=service_id,
        date=date_str,
        time=time_str,
        phone=phone,
        source="phone",
    )

    await state.clear()

    await message.answer(
        f"✅ <b>Запись создана!</b>\n\n"
        f"📞 Источник: <b>звонок</b>\n"
        f"📝 Услуга: {service_name}\n"
        f"📅 Дата: {date_str}\n"
        f"⏰ Время: {time_str}\n"
        f"👤 Клиент: {name}\n"
        f"📱 Телефон: {phone}\n\n"
        f"Посмотреть — /bookings_today",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "mb_cancel")
async def mb_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Создание записи отменено.")
    await callback.answer()


# =========================================================================
#                     БЛОКИРОВКА КЛИЕНТОВ
# =========================================================================

@router.message(Command("block"))
async def cmd_block(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
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
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"ℹ️ Клиент <code>{telegram_id}</code> уже заблокирован.",
            parse_mode="HTML",
        )


@router.message(Command("unblock"))
async def cmd_unblock(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Использование: /unblock <telegram_id>")
        return

    telegram_id = int(parts[1])
    removed = await rq.unblock_user(telegram_id)
    if removed:
        await message.answer(
            f"✅ Клиент <code>{telegram_id}</code> разблокирован.",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"ℹ️ Клиент <code>{telegram_id}</code> не был заблокирован.",
            parse_mode="HTML",
        )


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


# =========================================================================
#                       ЗАПИСИ НА СЕГОДНЯ
# =========================================================================

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
        user = await rq.get_user_by_id(b.user_id)
        service = services_map.get(b.service_id)
        service_name = service.name if service else "услуга удалена"
        src = _source_icon(b.source or "bot")

        text += f"🕐 <b>{b.time}</b> — {service_name} {src}\n"
        if user:
            text += f"👤 {user.first_name}"
            if user.username and not user.is_virtual:
                text += f" (@{user.username})"
            text += "\n"
            if not user.is_virtual:
                text += f"🆔 <code>{user.telegram_id}</code>\n"

        phone = b.phone or (user.phone if user else None)
        if phone:
            text += f"📱 {phone}\n"

        text += f"📅 {b.date}\n\n"

    text += f"<b>Всего: {len(bookings)}</b>\n"
    text += "🤖 — из бота, 📞 — по звонку"
    await message.answer(text, parse_mode="HTML")


# =========================================================================
#                       ЗАПИСИ ЗА НЕДЕЛЮ
# =========================================================================

@router.message(Command("bookings_week"))
async def cmd_bookings_week(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    today = today_salon()
    end_date = today + timedelta(days=6)

    bookings = await rq.get_bookings_for_period(
        today.isoformat(),
        end_date.isoformat(),
    )

    if not bookings:
        await message.answer(
            f"📭 Записей с {today.strftime('%d.%m')} "
            f"по {end_date.strftime('%d.%m')} нет."
        )
        return

    services = await rq.get_all_services(only_active=False)
    services_map = {s.id: s for s in services}

    text = f"📋 <b>Записи с {today.strftime('%d.%m')} по {end_date.strftime('%d.%m')}</b>\n\n"

    current_date = None
    for b in bookings:
        if b.date != current_date:
            current_date = b.date
            date_obj = datetime.fromisoformat(b.date).date()
            weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            weekday = weekdays[date_obj.weekday()]
            text += f"\n📅 <b>{b.date} ({weekday})</b>\n"

        user = await rq.get_user_by_id(b.user_id)
        service = services_map.get(b.service_id)
        service_name = service.name if service else "услуга удалена"
        src = _source_icon(b.source or "bot")

        text += f"  🕐 {b.time} — {service_name} {src}\n"
        if user:
            text += f"  👤 {user.first_name}"
            if user.username and not user.is_virtual:
                text += f" (@{user.username})"
            text += "\n"
            if not user.is_virtual:
                text += f"  🆔 <code>{user.telegram_id}</code>\n"

        phone = b.phone or (user.phone if user else None)
        if phone:
            text += f"  📱 {phone}\n"

    text += f"\n<b>Всего: {len(bookings)}</b>\n"
    text += "🤖 — из бота, 📞 — по звонку"
    await message.answer(text, parse_mode="HTML")


# =========================================================================
#                       ИНФОРМАЦИЯ О КЛИЕНТЕ
# =========================================================================

@router.message(Command("user"))
async def cmd_user(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "Использование: /user <telegram_id>\n"
            "Например: /user 575558031"
        )
        return

    telegram_id = int(parts[1])
    user = await rq.get_user_by_telegram_id(telegram_id)

    if user is None:
        await message.answer(
            f"❌ Клиент с ID <code>{telegram_id}</code> не найден.",
            parse_mode="HTML",
        )
        return

    total = await rq.get_user_bookings_count(user.id)
    active = await rq.get_user_active_bookings_count(user.id)
    blocked = await rq.is_blocked(telegram_id)

    text = (
        f"👤 <b>Информация о клиенте</b>\n\n"
        f"🆔 <code>{user.telegram_id}</code>\n"
        f"📝 Имя: {user.first_name}\n"
    )
    if user.username:
        text += f"💬 Username: @{user.username}\n"
    if user.phone:
        text += f"📱 Телефон: {user.phone}\n"

    text += (
        f"📅 Создан: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"📊 Всего записей: {total}\n"
        f"✅ Активных: {active}\n"
        f"🚫 Заблокирован: {'да' if blocked else 'нет'}\n"
    )

    await message.answer(text, parse_mode="HTML")


# =========================================================================
#                       ИСТОРИЯ ЗАПИСЕЙ КЛИЕНТА
# =========================================================================

@router.message(Command("history"))
async def cmd_history(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "Использование: /history <telegram_id>\n"
            "Например: /history 575558031"
        )
        return

    telegram_id = int(parts[1])
    user = await rq.get_user_by_telegram_id(telegram_id)

    if user is None:
        await message.answer(
            f"❌ Клиент с ID <code>{telegram_id}</code> не найден.",
            parse_mode="HTML",
        )
        return

    bookings = await rq.get_user_bookings(user.id)
    if not bookings:
        await message.answer(f"📭 У клиента {user.first_name} нет записей.")
        return

    services = await rq.get_all_services(only_active=False)
    services_map = {s.id: s for s in services}

    text = f"📋 <b>История записей: {user.first_name}</b>\n"
    text += f"🆔 <code>{user.telegram_id}</code>\n"
    if user.phone:
        text += f"📱 {user.phone}\n"
    text += "\n"

    for b in bookings[-15:]:
        service = services_map.get(b.service_id)
        service_name = service.name if service else "услуга удалена"
        status_emoji = "✅" if b.status != "cancelled" else "❌"
        src = _source_icon(b.source or "bot")

        line = f"{status_emoji} {b.date} {b.time} — {service_name} {src}"
        text += line + "\n"

    if len(bookings) > 15:
        text += f"\n... и ещё {len(bookings) - 15} записей"

    text += f"\n\n<b>Всего: {len(bookings)}</b>"
    await message.answer(text, parse_mode="HTML")


# =========================================================================
#                              СТАТИСТИКА
# =========================================================================

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    today = today_salon()
    start_date = today - timedelta(days=30)

    stats = await rq.get_stats_for_period(
        start_date.isoformat(),
        today.isoformat(),
    )

    if stats["total"] == 0:
        await message.answer(f"📭 За последние 30 дней записей нет.")
        return

    text = f"📊 <b>Статистика за 30 дней</b>\n"
    text += f"({start_date.strftime('%d.%m')} — {today.strftime('%d.%m')})\n\n"
    text += f"📋 Всего записей: <b>{stats['total']}</b>\n"
    text += f"✅ Активных: <b>{stats['active']}</b>\n"
    text += f"❌ Отменённых: <b>{stats['cancelled']}</b>\n"
    text += f"👥 Уникальных клиентов: <b>{stats['unique_users']}</b>\n\n"

    if stats["popular"]:
        text += f"🔥 <b>Популярные услуги:</b>\n"
        for i, (name, count) in enumerate(stats["popular"], 1):
            text += f"{i}. {name} — {count} раз\n"

    await message.answer(text, parse_mode="HTML")