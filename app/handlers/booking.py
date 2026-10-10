from datetime import date, timedelta
from aiogram import Router, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database import requests as rq

router = Router()

from datetime import date, datetime, timedelta, timezone

# Часовой пояс салона — UTC+5 (Уфа)
SALON_TZ = timezone(timedelta(hours=5)) # Время меняется посредством изменения цифры (Московское UTC 3)

def now_salon():
    """Текущее время в часовом поясе салона."""
    return datetime.now(SALON_TZ).replace(tzinfo=None)


def today_salon():
    """Сегодняшняя дата в часовом поясе салона."""
    return now_salon().date()

# ===== Состояния записи =====

class BookingFlow(StatesGroup):
    choosing_date = State()
    choosing_time = State()


# ===== Слоты времени (по 1 часу с 10:00 до 18:00) =====

ALL_TIMES = [f"{h:02d}:00" for h in range(10, 19)]


# ===== Клавиатура с датами =====

def dates_keyboard(service_id: int):
    builder = InlineKeyboardBuilder()
    today = date.today()
    weekdays_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    for i in range(7):
        d = today + timedelta(days=i)
        if i == 0:
            label = f"Сегодня, {d.strftime('%d.%m')}"
        elif i == 1:
            label = f"Завтра, {d.strftime('%d.%m')}"
        else:
            label = f"{weekdays_ru[d.weekday()]}, {d.strftime('%d.%m')}"
        builder.button(text=label, callback_data=f"date_{service_id}_{d.isoformat()}")

    builder.button(text="❌ Отмена", callback_data="cancel_booking")
    builder.adjust(1)
    return builder.as_markup()


# ===== Клавиатура со временем =====

from datetime import date, datetime, timedelta


async def times_keyboard(service_id: int, date_str: str):
    """Показывает только свободные слоты с учётом прошедшего времени (запас 2 часа)."""
    booked = await rq.get_booked_times(date_str)

    builder = InlineKeyboardBuilder()
    free_count = 0

    # Проверяем, сегодня ли выбранная дата
    today = date.today()
    is_today = date_str == today.isoformat()

    # Текущее время + 2 часа — минимальное доступное время
    now_plus_2h = datetime.now() + timedelta(hours=2)

    for t in ALL_TIMES:
        # Пропускаем занятые
        if t in booked:
            continue

        # Если выбрана СЕГОДНЯШНЯЯ дата — проверяем, не прошло ли время
        if is_today:
            hour, minute = map(int, t.split(":"))
            slot_time = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))

            # Пропускаем слоты, которые раньше чем через 2 часа
            if slot_time <= now_plus_2h:
                continue

        builder.button(text=t, callback_data=f"time_{service_id}_{date_str}_{t}")
        free_count += 1

    if free_count == 0:
        # Если всё занято или прошло
        builder.button(text="⬅️ Выбрать другую дату", callback_data=f"back_to_dates_{service_id}")
    else:
        builder.button(text="❌ Отмена", callback_data="cancel_booking")

    builder.adjust(3)
    return builder.as_markup()


# ===== Шаг 1: клиент выбрал услугу — показываем даты =====

async def start_booking(callback: types.CallbackQuery, state: FSMContext, service_id: int):
    services = await rq.get_all_services(only_active=True)
    service = next((s for s in services if s.id == service_id), None)

    if service is None:
        await callback.message.answer("❌ Услуга не найдена.")
        await callback.answer()
        return

    await state.update_data(service_id=service_id, service_name=service.name)
    await state.set_state(BookingFlow.choosing_date)

    await callback.message.answer(
        f"Ты выбрал: {service.name} — {service.price} ₽\n\n"
        f"📅 Выбери дату:",
        reply_markup=dates_keyboard(service_id)
    )
    await callback.answer()


# ===== Шаг 2: клиент выбрал дату — показываем время =====

@router.callback_query(F.data.startswith("date_"), BookingFlow.choosing_date)
async def cb_choose_date(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    service_id = int(parts[1])
    date_str = parts[2]

    await state.update_data(date=date_str)
    await state.set_state(BookingFlow.choosing_time)

    await callback.message.answer(
        f"📅 Дата: {date_str}\n\n⏰ Выбери время:",
        reply_markup=await times_keyboard(service_id, date_str)
    )
    await callback.answer()

# ===== Шаг 3: клиент выбрал время — сохраняем запись =====

@router.callback_query(F.data.startswith("time_"), BookingFlow.choosing_time)
async def cb_choose_time(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    service_id = int(parts[1])
    date_str = parts[2]
    time_str = parts[3]

    data = await state.get_data()

    # Проверяем, что слот всё ещё свободен
    booked = await rq.get_booked_times(date_str)
    if time_str in booked:
        await callback.message.answer(
            "⚠️ Это время уже занято. Выбери другое:",
            reply_markup=await times_keyboard(service_id, date_str)
        )
        await callback.answer()
        return

    # Проверяем, что время не в прошлом (с учётом запаса 2 часа)
    today = date.today()
    if date_str == today.isoformat():
        now_plus_2h = datetime.now() + timedelta(hours=2)
        hour, minute = map(int, time_str.split(":"))
        slot_time = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
        if slot_time <= now_plus_2h:
            await callback.message.answer(
                "⚠️ На это время уже нельзя записаться (нужно минимум за 2 часа). Выбери другое:",
                reply_markup=await times_keyboard(service_id, date_str)
            )
            await callback.answer()
            return

    # Получаем пользователя из БД
    user = await rq.get_or_create_user(
        telegram_id=callback.from_user.id,
        first_name=callback.from_user.first_name,
        username=callback.from_user.username,
    )

    await rq.create_booking(
        user_id=user.id,
        service_id=service_id,
        date=date_str,
        time=time_str,
    )

    await state.clear()

    await callback.message.answer(
        f"✅ Ты записан!\n\n"
        f"📝 Услуга: {data['service_name']}\n"
        f"📅 Дата: {date_str}\n"
        f"⏰ Время: {time_str}\n\n"
        f"Посмотреть свои записи: /my_bookings"
    )
    await callback.answer()

# ===== Отмена записи =====

@router.callback_query(F.data == "cancel_booking")
async def cb_cancel_flow(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Запись отменена.")
    await callback.answer()

    # ===== Вернуться к выбору даты =====

@router.callback_query(F.data.startswith("back_to_dates_"))
async def cb_back_to_dates(callback: types.CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[3])
    data = await state.get_data()
    service_name = data.get("service_name", "услуга")

    await state.set_state(BookingFlow.choosing_date)

    await callback.message.answer(
        f"Ты выбрал: {service_name}\n\n📅 Выбери дату:",
        reply_markup=dates_keyboard(service_id)
    )
    await callback.answer()