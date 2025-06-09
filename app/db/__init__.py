from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from common.app_settings import settings

engine = create_async_engine(settings.DB_CONNECTION_STRING, connect_args={})

SessionLocal = async_sessionmaker(
    autoflush=False, autocommit=False, bind=engine, expire_on_commit=False
)


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()


SessionContext = Annotated[AsyncSession, Depends(get_db)]
