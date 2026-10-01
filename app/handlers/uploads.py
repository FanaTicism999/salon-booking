import os
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from app import github_api

router = Router()

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Размер картинки — максимум 5 МБ (Telegram Bot API позволяет больше, но нам хватит)
MAX_FILE_SIZE = 5 * 1024 * 1024


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


class UploadFlow(StatesGroup):
    waiting_photo = State()


# ===== Карта: какая команда → какой путь + поле в site.json =====

UPLOAD_TARGETS = {
    "upload_hero": {
        "path": "landing/images/hero.jpg",
        "field": "hero_image",
        "value": "images/hero.jpg",
        "label": "фон главного экрана",
    },
    "upload_logo": {
        "path": "landing/images/logo.jpg",
        "field": "logo_image",
        "value": "images/logo.jpg",
        "label": "логотип",
    },
    "upload_service1": {
        "path": "landing/images/service-1.jpg",
        "field": None,   # для услуг поле не меняем, путь уже указан в site.json
        "value": None,
        "label": "фото услуги 1 (Стрижка женская)",
    },
    "upload_service2": {
        "path": "landing/images/service-2.jpg",
        "field": None,
        "value": None,
        "label": "фото услуги 2 (Стрижка мужская)",
    },
    "upload_service3": {
        "path": "landing/images/service-3.jpg",
        "field": None,
        "value": None,
        "label": "фото услуги 3 (Окрашивание)",
    },
    "upload_service4": {
        "path": "landing/images/service-4.jpg",
        "field": None,
        "value": None,
        "label": "фото услуги 4 (Маникюр)",
    },
    "upload_service5": {
        "path": "landing/images/service-5.jpg",
        "field": None,
        "value": None,
        "label": "фото услуги 5 (Педикюр)",
    },
    "upload_service6": {
        "path": "landing/images/service-6.jpg",
        "field": None,
        "value": None,
        "label": "фото услуги 6 (Массаж лица)",
    },
}


# ===== Универсальный обработчик команд загрузки =====

@router.message(Command(*UPLOAD_TARGETS.keys()))
async def cmd_upload(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав для этой команды.")
        return

    # Определяем, какая команда была вызвана
    cmd = message.text.split()[0].lstrip("/").split("@")[0]
    target = UPLOAD_TARGETS.get(cmd)

    if target is None:
        await message.answer("❓ Неизвестная команда загрузки.")
        return

    await state.update_data(target=target)
    await state.set_state(UploadFlow.waiting_photo)
    await message.answer(
        f"📸 Пришли фото для «{target['label']}»\n\n"
        f"⚠️ Требования:\n"
        f"• Формат: JPG или PNG\n"
        f"• Размер: до 5 МБ\n"
        f"• Отправь **как фото** (не как файл)"
    )


# ===== Обработка полученного фото =====

@router.message(UploadFlow.waiting_photo, F.photo)
async def handle_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав.")
        await state.clear()
        return

    data = await state.get_data()
    target = data.get("target")

    if not target:
        await message.answer("❌ Что-то пошло не так. Попробуй ещё раз.")
        await state.clear()
        return

    # Берём самую большую версию фото
    photo = message.photo[-1]

    if photo.file_size > MAX_FILE_SIZE:
        await message.answer(
            f"❌ Файл слишком большой ({photo.file_size // 1024 // 1024} МБ). "
            f"Максимум 5 МБ."
        )
        return

    await message.answer("⏳ Загружаю фото на GitHub...")

    try:
        # Скачиваем фото из Telegram
        file = await message.bot.get_file(photo.file_id)
        file_bytes = await message.bot.download_file(file.file_path)

        # Загружаем на GitHub
        await github_api.upload_file(
            file_path=target["path"],
            content_bytes=file_bytes.read(),
            commit_message=f"Загружено фото: {target['label']}",
        )

        # Если нужно — обновляем site.json (для hero, logo)
        if target["field"] and target["value"]:
            await github_api.update_field(target["field"], target["value"])

        await message.answer(
            f"✅ Фото загружено!\n\n"
            f"📸 {target['label']}\n\n"
            f"🌐 Сайт обновится через 30-60 секунд:\n"
            f"https://salon-booking-bht.pages.dev"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка загрузки: {e}")

    await state.clear()


# ===== Обработка случая, когда прислали не фото =====

@router.message(UploadFlow.waiting_photo)
async def handle_not_photo(message: types.Message):
    await message.answer(
        "⚠️ Нужно прислать именно **фото** (не файл, не текст).\n"
        "Попробуй ещё раз."
    )