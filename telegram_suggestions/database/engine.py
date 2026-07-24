from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from ..config import config
from models import Base

engine = create_async_engine(config.DB_URL, echo=False)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Создание таблиц в БД, если они еще не существуют"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)