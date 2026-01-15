from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

from src.config import config
from sqlalchemy.ext.asyncio import AsyncSession


url = config.DATABASE_URL
engine = create_async_engine(url)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session



