import os
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from app import github_api

router = Router()

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


class EditField(StatesGroup):
    waiting_value = State()


# ===== Универсальный обработчик редактирования =====

FIELD_NAMES = {
    "edit_name": ("salon_name", "название салона"),
    "edit_hero_title": ("hero_title", "заголовок на главной"),
    "edit_hero_subtitle": ("hero_subtitle", "слоган на главной"),
    "edit_phone": ("phone", "телефон"),
    "edit_address": ("address", "адрес"),
}


@router.message(Command(*FIELD_NAMES.keys()))
async def cmd_edit_field(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    # Определяем, какая команда была вызвана
    cmd = message.text.split()[0].lstrip("/").split("@")[0]
    field_name, label = FIELD_NAMES.get(cmd, (None, None))

    if field_name is None:
        await message.answer("❓ Неизвестная команда редактирования.")
        return

    await state.update_data(field_name=field_name, label=label)
    await state.set_state(EditField.waiting_value)
    await message.answer(f"✏️ Введи новое значение для «{label}»:")


@router.message(EditField.waiting_value)
async def save_new_value(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав.")
        await state.clear()
        return

    data = await state.get_data()
    field_name = data["field_name"]
    label = data["label"]
    new_value = message.text.strip()

    # Показываем «печатает...»
    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        await github_api.update_field(field_name, new_value)
        await message.answer(
            f"✅ Обновлено!\n\n"
            f"📝 {label}: {new_value}\n\n"
            f"🌐 Сайт обновится через 30–60 секунд:\n"
            f"https://salon-booking-bht.pages.dev"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при обновлении: {e}")

    await state.clear()


# ===== Просмотр текущих данных =====

@router.message(Command("show_site"))
async def cmd_show_site(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    try:
        data, _ = await github_api.get_site_json()
        text = (
            f"📋 Текущие данные сайта:\n\n"
            f"🏢 Название: {data.get('salon_name')}\n"
            f"🎯 Заголовок: {data.get('hero_title')}\n"
            f"💬 Слоган: {data.get('hero_subtitle')}\n"
            f"📞 Телефон: {data.get('phone')}\n"
            f"📍 Адрес: {data.get('address')}\n\n"
            f"✏️ Команды для изменения:\n"
            f"/edit_name — название\n"
            f"/edit_hero_title — заголовок\n"
            f"/edit_hero_subtitle — слоган\n"
            f"/edit_phone — телефон\n"
            f"/edit_address — адрес"
        )
        await message.answer(text)
    except Exception as e:
        await message.answer(f"❌ Ошибка чтения: {e}")