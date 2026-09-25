from sqlalchemy import select
from app.database.engine import async_session
from app.database.models import Service, User, Booking


# ===== Пользователи =====

async def get_or_create_user(telegram_id: int, first_name: str, username: str | None) -> User:
    """Возвращает пользователя из БД или создаёт нового."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                username=username,
                role="client",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user


# ===== Услуги =====

async def add_service(name: str, price: int, duration: int) -> Service:
    """Добавляет новую услугу."""
    async with async_session() as session:
        service = Service(name=name, price=price, duration=duration)
        session.add(service)
        await session.commit()
        await session.refresh(service)
        return service


async def get_all_services(only_active: bool = True) -> list[Service]:
    """Возвращает список услуг."""
    async with async_session() as session:
        query = select(Service)
        if only_active:
            query = query.where(Service.is_active == True)
        query = query.order_by(Service.id)
        result = await session.execute(query)
        return list(result.scalars().all())


async def delete_service(service_id: int) -> bool:
    """Удаляет услугу по ID."""
    async with async_session() as session:
        result = await session.execute(
            select(Service).where(Service.id == service_id)
        )
        service = result.scalar_one_or_none()
        if service is None:
            return False
        await session.delete(service)
        await session.commit()
        return True