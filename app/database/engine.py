from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.models import Base

# Файл базы данных будет лежать в корне проекта: salon.db
DATABASE_URL = "sqlite+aiosqlite:///salon.db"

engine = create_async_engine(DATABASE_URL, echo=False)

# Фабрика сессий — через неё делаем запросы к БД
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Создаёт все таблицы, если их ещё нет."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)