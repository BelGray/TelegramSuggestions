import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from telegram_suggestions.database.engine import async_session
from telegram_suggestions.database.models import User, Channel, ChannelAdmin, Message, ChannelBan


# ==================== ПОЛЬЗОВАТЕЛИ ====================

async def get_or_create_user(user_id: int, language_code: str = "ru") -> User:
    """Получить пользователя или создать нового, если его нет"""
    async with async_session() as session:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # Ограничиваем язык четырьмя поддерживаемыми
            lang = language_code if language_code in ["ru", "en", "hi", "es"] else "en"
            user = User(id=user_id, language_code=lang)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user


async def set_user_language(user_id: int, language_code: str):
    """Обновить язык интерфейса пользователя"""
    async with async_session() as session:
        stmt = update(User).where(User.id == user_id).values(language_code=language_code)
        await session.execute(stmt)
        await session.commit()


# ==================== КАНАЛЫ И АДМИНЫ ====================

def _generate_unique_hash() -> str:
    """Генерация короткого 8-символьного хэша для ссылки"""
    return secrets.token_urlsafe(6)


async def create_channel(channel_id: int, owner_id: int) -> Channel:
    """Создать канал и назначить владельца"""
    async with async_session() as session:
        # Проверяем, существует ли уже этот канал
        stmt = select(Channel).where(Channel.id == channel_id)
        res = await session.execute(stmt)
        existing_channel = res.scalar_one_or_none()

        if existing_channel:
            return existing_channel

        # Генерируем уникальный хэш ссылки
        deep_link_hash = _generate_unique_hash()

        channel = Channel(id=channel_id, deep_link_hash=deep_link_hash)
        session.add(channel)

        # Добавляем создателя в таблицу админов с флагом is_owner=True
        admin = ChannelAdmin(channel_id=channel_id, user_id=owner_id, is_owner=True)
        session.add(admin)

        await session.commit()
        await session.refresh(channel)
        return channel


async def get_channel_by_hash(deep_link_hash: str) -> Optional[Channel]:
    """Найти канал по хэшу из deep-link ссылки"""
    async with async_session() as session:
        stmt = select(Channel).where(Channel.deep_link_hash == deep_link_hash)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()


async def get_channel_by_id(channel_id: int) -> Optional[Channel]:
    """Получить канал по ID"""
    async with async_session() as session:
        stmt = select(Channel).where(Channel.id == channel_id)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()


async def get_user_channels(user_id: int) -> List[Channel]:
    """Получить список всех каналов, админом которых является пользователь"""
    async with async_session() as session:
        stmt = select(Channel).join(ChannelAdmin).where(ChannelAdmin.user_id == user_id)
        res = await session.execute(stmt)
        return list(res.scalars().all())


async def update_channel_settings(channel_id: int, new_settings: Dict[str, Any]):
    """Обновить настройки кнопок канала"""
    async with async_session() as session:
        stmt = update(Channel).where(Channel.id == channel_id).values(settings=new_settings)
        await session.execute(stmt)
        await session.commit()


async def add_admin(channel_id: int, user_id: int, is_owner: bool = False) -> bool:
    """Добавить админа к каналу"""
    async with async_session() as session:
        stmt = select(ChannelAdmin).where(
            ChannelAdmin.channel_id == channel_id,
            ChannelAdmin.user_id == user_id
        )
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            return False  # Уже админ

        admin = ChannelAdmin(channel_id=channel_id, user_id=user_id, is_owner=is_owner)
        session.add(admin)
        await session.commit()
        return True


async def get_channel_admins(channel_id: int) -> List[ChannelAdmin]:
    """Получить всех зарегистрированных админов канала"""
    async with async_session() as session:
        stmt = select(ChannelAdmin).where(ChannelAdmin.channel_id == channel_id)
        res = await session.execute(stmt)
        return list(res.scalars().all())


async def get_admin_record(channel_id: int, user_id: int) -> Optional[ChannelAdmin]:
    """Получить конкретную запись настройки админа"""
    async with async_session() as session:
        stmt = select(ChannelAdmin).where(
            ChannelAdmin.channel_id == channel_id,
            ChannelAdmin.user_id == user_id
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()


async def update_admin_personal_settings(channel_id: int, user_id: int, accepts: bool, display_type: str):
    """Обновить персональные настройки админа (прием личных вопросов и тип имени)"""
    async with async_session() as session:
        stmt = update(ChannelAdmin).where(
            ChannelAdmin.channel_id == channel_id,
            ChannelAdmin.user_id == user_id
        ).values(accepts_direct_questions=accepts, display_type=display_type)
        await session.execute(stmt)
        await session.commit()


# ==================== СООБЩЕНИЯ, ОТЗЫВЫ И РЕЙТИНГ ====================

async def add_message(
    channel_id: int,
    sender_id: int,
    msg_type: str,
    is_anonymous: bool,
    text: Optional[str] = None,
    media_file_id: Optional[str] = None,
    media_type: Optional[str] = None,
    target_admin_id: Optional[int] = None,
    rating_value: Optional[int] = None
) -> Message:
    """Сохранить сообщение (идея, вопрос, отзыв)"""
    async with async_session() as session:
        # Если это отзыв — проверяем, оставлял ли юзер отзыв раньше и обновляем его
        if msg_type == "review":
            stmt = select(Message).where(
                Message.channel_id == channel_id,
                Message.sender_id == sender_id,
                Message.type == "review"
            )
            res = await session.execute(stmt)
            existing_review = res.scalar_one_or_none()

            if existing_review:
                existing_review.rating_value = rating_value
                existing_review.text = text
                existing_review.updated_at = datetime.now()
                await session.commit()
                await session.refresh(existing_review)
                return existing_review

        # Если нового типа или другое сообщение
        msg = Message(
            channel_id=channel_id,
            sender_id=sender_id,
            target_admin_id=target_admin_id,
            type=msg_type,
            is_anonymous=is_anonymous,
            text=text,
            media_file_id=media_file_id,
            media_type=media_type,
            rating_value=rating_value
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)
        return msg


async def get_channel_rating(channel_id: int) -> Tuple[int, float]:
    """Динамический подсчет количества и среднего рейтинга канала"""
    async with async_session() as session:
        stmt = select(
            func.count(Message.rating_value),
            func.avg(Message.rating_value)
        ).where(
            Message.channel_id == channel_id,
            Message.type == "review",
            Message.rating_value.is_not(None)
        )
        res = await session.execute(stmt)
        count, avg = res.first()
        return (count or 0, round(float(avg), 1) if avg else 0.0)


async def check_review_cooldown(channel_id: int, sender_id: int) -> Tuple[bool, Optional[int]]:
    """
    Проверка кулдауна на повторный отзыв (1 неделя / 7 дней).
    Возвращает (can_review: bool, days_remaining: int)
    """
    async with async_session() as session:
        stmt = select(Message).where(
            Message.channel_id == channel_id,
            Message.sender_id == sender_id,
            Message.type == "review"
        )
        res = await session.execute(stmt)
        review = res.scalar_one_or_none()

        if not review:
            return True, None

        next_available_date = review.updated_at + timedelta(days=7)
        now = datetime.now()

        if now >= next_available_date:
            return True, None
        else:
            days_left = (next_available_date - now).days + 1
            return False, days_left


# ==================== БАНЫ ====================

async def is_user_banned(channel_id: int, user_id: int) -> bool:
    """Проверка, забанен ли пользователь в канале"""
    async with async_session() as session:
        stmt = select(ChannelBan).where(
            ChannelBan.channel_id == channel_id,
            ChannelBan.user_id == user_id
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none() is not None


async def ban_user(channel_id: int, user_id: int):
    """Забанить пользователя в конкретном канале"""
    async with async_session() as session:
        if not await is_user_banned(channel_id, user_id):
            ban = ChannelBan(channel_id=channel_id, user_id=user_id)
            session.add(ban)
            await session.commit()


async def unban_user(channel_id: int, user_id: int):
    """Разбанить пользователя в канале"""
    async with async_session() as session:
        stmt = delete(ChannelBan).where(
            ChannelBan.channel_id == channel_id,
            ChannelBan.user_id == user_id
        )
        await session.execute(stmt)
        await session.commit()


async def get_banned_users(channel_id: int) -> List[ChannelBan]:
    """Получить список всех забаненных пользователей канала"""
    async with async_session() as session:
        stmt = select(ChannelBan).where(ChannelBan.channel_id == channel_id)
        res = await session.execute(stmt)
        return list(res.scalars().all())