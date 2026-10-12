"""
Инициализация пакета app.
Здесь загружаем .env ДО того, как любой модуль app прочитает os.getenv().
"""
from dotenv import load_dotenv

load_dotenv()