import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.media import MediaFile


async def get_media_file_path(db: AsyncSession, file_id: int) -> str | None:
    """Fetches the file path from the database and verifies it exists on disk."""
    stmt = select(MediaFile).where(MediaFile.id == file_id)
    result = await db.execute(stmt)
    media_file = result.scalars().first()

    if not media_file or not os.path.exists(media_file.file_path):
        return None

    return media_file.file_path
