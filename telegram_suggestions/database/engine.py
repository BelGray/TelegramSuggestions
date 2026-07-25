from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import config
from database.models import Base

# Добавлены pool_pre_ping и pool_recycle для защиты от усыпления соединений Neon.tech
engine = create_async_engine(
    config.DB_URL,
    echo=False,
    pool_recycle=300,   # Авто-обновление подключений каждые 5 минут
    pool_pre_ping=True  # Авто-проверка живости соединения перед каждым запросом
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Создание таблиц в БД, если они еще не существуют"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)