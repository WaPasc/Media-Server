import asyncio

from core.database import engine
from models.base import Base


async def init_database() -> None:
    print('Creating database tables')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Tables created succesfully')


if __name__ == '__main__':
    asyncio.run(init_database())
