import os
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from app.database import requests as rq

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