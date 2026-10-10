import os
from aiogram import Router, types
from aiogram.filters import Command

router = Router()

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ===== Справка для админа =====

ADMIN_HELP = """
📚 <b>Все команды бота</b>

<b>📋 Работа с услугами</b>
/add_service — добавить услугу
/list_services — список услуг
/del_service &lt;id&gt; — удалить услугу

<b>✏️ Редактирование сайта</b>
/show_site — текущие данные сайта
/edit_name — название салона
/edit_hero_title — заголовок на главной
/edit_hero_subtitle — слоган
/edit_phone — телефон
/edit_address — адрес

<b>📸 Загрузка фото</b>
/upload_hero — фон главной
/upload_logo — логотип
/upload_service1 ... /upload_service9 — фото услуг

<b>ℹ️ Прочее</b>
/help — эта справка

💡 <i>Все изменения сайта появляются на нём через 30-60 секунд.</i>
"""


# ===== Справка для клиента =====

CLIENT_HELP = """
📚 <b>Что я умею</b>

📝 <b>Записаться на услугу</b>
Нажми кнопку "📝 Записаться" — выбери услугу, дату и время.

📋 <b>Мои записи</b>
Нажми "📋 Мои записи" — посмотреть или отменить.

ℹ️ <b>О нас</b>
Нажми "ℹ️ О нас" — информация о салоне.

❓ <b>Вопросы</b>
Если что-то непонятно — обратись к администратору.
"""


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer(ADMIN_HELP, parse_mode="HTML")
    else:
        await message.answer(CLIENT_HELP, parse_mode="HTML")