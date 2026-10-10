import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.models import Base

# На Render DATABASE_URL берётся из переменных окружения (Neon)
# Локально используется SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///salon.db")

# asyncpg требует префикс postgresql+asyncpg://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# asyncpg не понимает sslmode — убираем его из URL и передаём через connect_args
connect_args = {}
if "postgresql" in DATABASE_URL:
    # Убираем параметры, которые не понимает asyncpg
    if "?" in DATABASE_URL:
        base, params = DATABASE_URL.split("?", 1)
        # Фильтруем параметры — оставляем только те, что понимает asyncpg
        allowed = []
        for param in params.split("&"):
            if param.startswith("channel_binding"):
                continue  # asyncpg не понимает
            if param.startswith("sslmode"):
                # sslmode=require → передаём через connect_args
                continue
            allowed.append(param)
        if allowed:
            DATABASE_URL = base + "?" + "&".join(allowed)
        else:
            DATABASE_URL = base
    # Если был sslmode — включаем SSL через connect_args
    if "sslmode=require" in os.getenv("DATABASE_URL", ""):
        connect_args["ssl"] = "require"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Создаёт все таблицы, если их ещё нет."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)