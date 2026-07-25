import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy import select, func, update, delete
from database.engine import async_session
from database.models import User, Channel, ChannelAdmin, Message, ChannelBan, AdminNotification


async def get_or_create_user(user_id: int, language_code: str = "ru") -> User:
    async with async_session() as session:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            lang = language_code if language_code in ["ru", "en", "hi", "es"] else "en"
            user = User(id=user_id, language_code=lang)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user


async def is_user_channel_admin(channel_id: int, user_id: int) -> bool:
    """Безопасная проверка прав админа перед выполнением действий"""
    async with async_session() as session:
        stmt = select(ChannelAdmin).where(
            ChannelAdmin.channel_id == channel_id,
            ChannelAdmin.user_id == user_id
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none() is not None


async def create_channel(channel_id: int, owner_id: int) -> Channel:
    async with async_session() as session:
        stmt = select(Channel).where(Channel.id == channel_id)
        res = await session.execute(stmt)
        existing_channel = res.scalar_one_or_none()

        if existing_channel:
            return existing_channel

        deep_link_hash = secrets.token_urlsafe(6)
        channel = Channel(id=channel_id, deep_link_hash=deep_link_hash)
        session.add(channel)

        admin = ChannelAdmin(channel_id=channel_id, user_id=owner_id, is_owner=True)
        session.add(admin)

        await session.commit()
        await session.refresh(channel)
        return channel


async def get_channel_by_hash(deep_link_hash: str) -> Optional[Channel]:
    async with async_session() as session:
        stmt = select(Channel).where(Channel.deep_link_hash == deep_link_hash)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()


async def get_channel_by_id(channel_id: int) -> Optional[Channel]:
    async with async_session() as session:
        stmt = select(Channel).where(Channel.id == channel_id)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()


async def get_user_channels(user_id: int) -> List[Channel]:
    async with async_session() as session:
        stmt = select(Channel).join(ChannelAdmin).where(ChannelAdmin.user_id == user_id)
        res = await session.execute(stmt)
        return list(res.scalars().all())


async def is_channel_premium(channel: Optional[Channel]) -> bool:
    if not channel or not channel.is_premium:
        return False
    if channel.premium_until is None:
        return True
    return channel.premium_until > datetime.now()


async def activate_channel_premium(channel_id: int, plan: str):
    async with async_session() as session:
        stmt = select(Channel).where(Channel.id == channel_id)
        res = await session.execute(stmt)
        channel = res.scalar_one_or_none()

        if not channel:
            return

        now = datetime.now()
        start_from = channel.premium_until if (channel.is_premium and channel.premium_until and channel.premium_until > now) else now

        if plan == "1d":
            until = start_from + timedelta(days=1)
        elif plan == "7d":
            until = start_from + timedelta(days=7)
        elif plan == "1m":
            until = start_from + timedelta(days=30)
        elif plan == "3m":
            until = start_from + timedelta(days=90)
        else:
            until = None

        channel.is_premium = True
        channel.premium_until = until
        await session.commit()


async def update_channel_settings(channel_id: int, new_settings: Dict[str, Any]):
    async with async_session() as session:
        stmt = update(Channel).where(Channel.id == channel_id).values(settings=new_settings)
        await session.execute(stmt)
        await session.commit()


async def set_channel_welcome_message(channel_id: int, welcome_text: Optional[str]):
    async with async_session() as session:
        stmt = update(Channel).where(Channel.id == channel_id).values(welcome_message=welcome_text)
        await session.execute(stmt)
        await session.commit()


async def set_channel_auto_reply(channel_id: int, auto_reply_text: Optional[str]):
    async with async_session() as session:
        stmt = update(Channel).where(Channel.id == channel_id).values(auto_reply=auto_reply_text)
        await session.execute(stmt)
        await session.commit()


async def add_admin(channel_id: int, user_id: int, is_owner: bool = False) -> bool:
    async with async_session() as session:
        stmt = select(ChannelAdmin).where(
            ChannelAdmin.channel_id == channel_id,
            ChannelAdmin.user_id == user_id
        )
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            return False

        admin = ChannelAdmin(channel_id=channel_id, user_id=user_id, is_owner=is_owner)
        session.add(admin)
        await session.commit()
        return True


async def get_channel_admins(channel_id: int) -> List[ChannelAdmin]:
    async with async_session() as session:
        stmt = select(ChannelAdmin).where(ChannelAdmin.channel_id == channel_id)
        res = await session.execute(stmt)
        return list(res.scalars().all())


async def get_admin_record(channel_id: int, user_id: int) -> Optional[ChannelAdmin]:
    async with async_session() as session:
        stmt = select(ChannelAdmin).where(
            ChannelAdmin.channel_id == channel_id,
            ChannelAdmin.user_id == user_id
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()


async def update_admin_personal_settings(channel_id: int, user_id: int, accepts: bool, display_type: str):
    async with async_session() as session:
        stmt = update(ChannelAdmin).where(
            ChannelAdmin.channel_id == channel_id,
            ChannelAdmin.user_id == user_id
        ).values(accepts_direct_questions=accepts, display_type=display_type)
        await session.execute(stmt)
        await session.commit()


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
    async with async_session() as session:
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


async def is_user_banned(channel_id: int, user_id: int) -> bool:
    async with async_session() as session:
        stmt = select(ChannelBan).where(
            ChannelBan.channel_id == channel_id,
            ChannelBan.user_id == user_id
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none() is not None


async def ban_user(channel_id: int, user_id: int):
    """Безопасный бан без гонки потоков (TOCTOU)"""
    async with async_session() as session:
        if not await is_user_banned(channel_id, user_id):
            try:
                ban = ChannelBan(channel_id=channel_id, user_id=user_id)
                session.add(ban)
                await session.commit()
            except Exception:
                await session.rollback()


async def unban_user(channel_id: int, user_id: int):
    async with async_session() as session:
        stmt = delete(ChannelBan).where(
            ChannelBan.channel_id == channel_id,
            ChannelBan.user_id == user_id
        )
        await session.execute(stmt)
        await session.commit()


async def get_banned_users(channel_id: int) -> List[ChannelBan]:
    async with async_session() as session:
        stmt = select(ChannelBan).where(ChannelBan.channel_id == channel_id)
        res = await session.execute(stmt)
        return list(res.scalars().all())


async def add_admin_notification(db_message_id: int, admin_user_id: int, telegram_message_id: int):
    async with async_session() as session:
        notif = AdminNotification(
            db_message_id=db_message_id,
            admin_user_id=admin_user_id,
            telegram_message_id=telegram_message_id
        )
        session.add(notif)
        await session.commit()


async def get_admin_notifications(db_message_id: int) -> List[AdminNotification]:
    async with async_session() as session:
        stmt = select(AdminNotification).where(AdminNotification.db_message_id == db_message_id)
        res = await session.execute(stmt)
        return list(res.scalars().all())


async def get_channel_stats(channel_id: int) -> Dict[str, Any]:
    async with async_session() as session:
        res_ideas = await session.execute(
            select(func.count(Message.id)).where(Message.channel_id == channel_id, Message.type == "idea")
        )
        ideas_count = res_ideas.scalar() or 0

        res_q = await session.execute(
            select(func.count(Message.id)).where(
                Message.channel_id == channel_id,
                Message.type.in_(["question_all", "question_admin"])
            )
        )
        questions_count = res_q.scalar() or 0

        res_rev = await session.execute(
            select(func.count(Message.id), func.avg(Message.rating_value)).where(
                Message.channel_id == channel_id, Message.type == "review"
            )
        )
        rev_count, rev_avg = res_rev.first()
        rev_count = rev_count or 0
        rev_avg = round(float(rev_avg), 1) if rev_avg else 0.0

        res_proc = await session.execute(
            select(func.count(Message.id)).where(
                Message.channel_id == channel_id,
                Message.status.in_(["answered", "published"])
            )
        )
        processed_count = res_proc.scalar() or 0

        return {
            "ideas_count": ideas_count,
            "questions_count": questions_count,
            "reviews_count": rev_count,
            "rating_avg": rev_avg,
            "processed_count": processed_count
        }


async def get_channel_reviews_for_export(channel_id: int) -> List[Message]:
    async with async_session() as session:
        stmt = select(Message).where(
            Message.channel_id == channel_id,
            Message.type == "review"
        ).order_by(Message.created_at.desc())
        res = await session.execute(stmt)
        return list(res.scalars().all())

async def set_channel_language(channel_id: int, language_code: str):
    """Смена языка публикаций для канала"""
    async with async_session() as session:
        stmt = update(Channel).where(Channel.id == channel_id).values(language_code=language_code)
        await session.execute(stmt)
        await session.commit()