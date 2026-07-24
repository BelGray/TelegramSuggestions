from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import BigInteger, String, Text, Boolean, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    """Пользователи бота (подписчики и админы)"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)  # Telegram ID
    language_code: Mapped[str] = mapped_column(String(10), default="ru")
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Channel(Base):
    """Каналы, подключенные к боту"""
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)  # Telegram Chat ID
    deep_link_hash: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    # Премиум настройки
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    welcome_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Кастомное приветствие
    auto_reply: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Авто-ответ подписчику

    # Настройки кнопок в JSON: {"ideas": True, "questions_all": True, "reviews": True, "show_copyright": True}
    settings: Mapped[Dict[str, Any]] = mapped_column(JSON, default=lambda: {
        "ideas": True,
        "questions_all": True,
        "reviews": True,
        "show_copyright": True
    })

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ChannelAdmin(Base):
    """Связь админов с каналами"""
    __tablename__ = "channel_admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("channels.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    accepts_direct_questions: Mapped[bool] = mapped_column(Boolean, default=True)
    display_type: Mapped[str] = mapped_column(String(20), default="anon")  # 'anon', 'name', 'username'
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False)


class Message(Base):
    """Сообщения: Идеи, Вопросы, Отзывы"""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("channels.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_admin_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"),
                                                           nullable=True)

    type: Mapped[str] = mapped_column(String(20))  # 'idea', 'question_all', 'question_admin', 'review'
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=True)

    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'photo', 'video', 'voice', etc.

    rating_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    status: Mapped[str] = mapped_column(String(20), default="pending")  # 'pending', 'answered', 'published', 'declined'

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ChannelBan(Base):
    """Бано-лист пользователей для каждого канала"""
    __tablename__ = "channel_bans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("channels.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())