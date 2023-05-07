from sys import modules

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from config.settings import settings

database_url = settings.main_database_url if 'pytest' not in modules else settings.test_database_url
async_engine = create_async_engine(database_url, echo=False)
async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)

Base = declarative_base()


async def get_async_session():
    async with async_session_maker() as session:
        yield session

