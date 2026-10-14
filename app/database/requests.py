import time
from sqlalchemy import select, func
from app.database.engine import async_session
from app.database.models import Service, User, Booking, BlockedUser

# ===== Пользователи =====

async def get_or_create_user(
    telegram_id: int,
    first_name: str,
    username: str | None,
    phone: str | None = None,
) -> User:
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
                phone=phone,
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

# ===== Записи =====

async def create_booking(
    user_id: int,
    service_id: int,
    date: str,
    time: str,
    phone: str | None = None,
    source: str = "bot",
) -> Booking:
    """Создаёт новую запись."""
    async with async_session() as session:
        booking = Booking(
            user_id=user_id,
            service_id=service_id,
            date=date,
            time=time,
            phone=phone,
            source=source,
            status="pending",
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)
        return booking

async def get_user_bookings(user_id: int) -> list[Booking]:
    """Возвращает все записи пользователя."""
    async with async_session() as session:
        query = (
            select(Booking)
            .where(Booking.user_id == user_id)
            .order_by(Booking.date, Booking.time)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

async def get_booked_times(date: str) -> list[str]:
    """Возвращает список занятых времён на дату."""
    async with async_session() as session:
        query = select(Booking.time).where(
            Booking.date == date,
            Booking.status != "cancelled",
        )
        result = await session.execute(query)
        return [row[0] for row in result.all()]

    

async def get_booking_by_id(booking_id: int) -> Booking | None:
    """Возвращает запись по ID."""
    async with async_session() as session:
        result = await session.execute(
            select(Booking).where(Booking.id == booking_id)
        )
        return result.scalar_one_or_none()


async def cancel_booking(booking_id: int) -> bool:
    """Меняет статус записи на cancelled."""
    async with async_session() as session:
        result = await session.execute(
            select(Booking).where(Booking.id == booking_id)
        )
        booking = result.scalar_one_or_none()
        if booking is None:
            return False
        booking.status = "cancelled"
        await session.commit()
        return True

async def update_user_phone(user_id: int, phone: str) -> bool:
    """Обновляет телефон пользователя."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return False
        user.phone = phone
        await session.commit()
        return True

# ===== Блокировка пользователей =====

async def block_user(telegram_id: int, reason: str | None = None) -> bool:
    """Блокирует пользователя. Возвращает True, если заблокирован впервые."""
    async with async_session() as session:
        # Проверяем, не заблокирован ли уже
        result = await session.execute(
            select(BlockedUser).where(BlockedUser.telegram_id == telegram_id)
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            return False  # уже был заблокирован

        blocked = BlockedUser(telegram_id=telegram_id, reason=reason)
        session.add(blocked)
        await session.commit()
        return True


async def unblock_user(telegram_id: int) -> bool:
    """Разблокирует пользователя. Возвращает True, если был заблокирован."""
    async with async_session() as session:
        result = await session.execute(
            select(BlockedUser).where(BlockedUser.telegram_id == telegram_id)
        )
        blocked = result.scalar_one_or_none()

        if blocked is None:
            return False

        await session.delete(blocked)
        await session.commit()
        return True


async def is_blocked(telegram_id: int) -> bool:
    """Проверяет, заблокирован ли пользователь."""
    async with async_session() as session:
        result = await session.execute(
            select(BlockedUser).where(BlockedUser.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none() is not None


async def get_blocked_users() -> list[BlockedUser]:
    """Возвращает список всех заблокированных."""
    async with async_session() as session:
        result = await session.execute(
            select(BlockedUser).order_by(BlockedUser.blocked_at.desc())
        )
        return list(result.scalars().all())


# ===== Записи на дату =====

async def get_bookings_for_date(date_str: str) -> list[Booking]:
    """Возвращает все активные записи на указанную дату."""
    async with async_session() as session:
        query = (
            select(Booking)
            .where(Booking.date == date_str, Booking.status != "cancelled")
            .order_by(Booking.time)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

async def get_user_by_id(user_id: int) -> User | None:
    """Возвращает пользователя по внутреннему ID."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

async def get_bookings_for_period(start_date: str, end_date: str) -> list[Booking]:
    """Возвращает активные записи за период [start_date, end_date]."""
    async with async_session() as session:
        query = (
            select(Booking)
            .where(
                Booking.date >= start_date,
                Booking.date <= end_date,
                Booking.status != "cancelled",
            )
            .order_by(Booking.date, Booking.time)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

# ===== Информация о клиенте =====

async def get_user_bookings_count(user_id: int) -> int:
    """Возвращает количество всех записей пользователя."""
    async with async_session() as session:
        result = await session.execute(
            select(func.count(Booking.id)).where(Booking.user_id == user_id)
        )
        return result.scalar_one()


async def get_user_active_bookings_count(user_id: int) -> int:
    """Возвращает количество активных записей."""
    async with async_session() as session:
        result = await session.execute(
            select(func.count(Booking.id)).where(
                Booking.user_id == user_id,
                Booking.status != "cancelled",
            )
        )
        return result.scalar_one()


# ===== Статистика =====

async def get_stats_for_period(start_date: str, end_date: str) -> dict:
    """Возвращает статистику за период."""
    async with async_session() as session:

        # Всего записей (включая отменённые)
        total = await session.execute(
            select(func.count(Booking.id)).where(
                Booking.date >= start_date,
                Booking.date <= end_date,
            )
        )
        total_count = total.scalar_one()

        # Активных (не отменённых)
        active = await session.execute(
            select(func.count(Booking.id)).where(
                Booking.date >= start_date,
                Booking.date <= end_date,
                Booking.status != "cancelled",
            )
        )
        active_count = active.scalar_one()

        # Отменённых
        cancelled = total_count - active_count

        # Популярные услуги (топ-5)
        popular = await session.execute(
            select(
                Service.name,
                func.count(Booking.id).label("cnt")
            )
            .join(Booking, Booking.service_id == Service.id)
            .where(
                Booking.date >= start_date,
                Booking.date <= end_date,
                Booking.status != "cancelled",
            )
            .group_by(Service.name)
            .order_by(func.count(Booking.id).desc())
            .limit(5)
        )
        popular_list = [(row[0], row[1]) for row in popular.all()]

        # Уникальных клиентов
        unique_users = await session.execute(
            select(func.count(func.distinct(Booking.user_id))).where(
                Booking.date >= start_date,
                Booking.date <= end_date,
                Booking.status != "cancelled",
            )
        )
        unique_users_count = unique_users.scalar_one()

        return {
            "total": total_count,
            "active": active_count,
            "cancelled": cancelled,
            "unique_users": unique_users_count,
            "popular": popular_list,
        }

async def get_user_by_telegram_id(telegram_id: int) -> User | None:
    """Возвращает пользователя по telegram_id."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

async def create_virtual_user(first_name: str, phone: str) -> User:
    """Создаёт 'виртуального' пользователя для записей по звонку."""
    async with async_session() as session:
        virtual_id = -int(time.time() * 1000)

        user = User(
            telegram_id=virtual_id,
            first_name=first_name,
            username=None,
            phone=phone,
            is_virtual=True,
            role="client",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user