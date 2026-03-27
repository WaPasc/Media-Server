import mimetypes

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.services.stream_service import get_media_file_path
from app.utils.video import generate_ffmpeg_stream

router = APIRouter(prefix='/api', tags=['stream'])


@router.get('/stream/{file_id}')
async def stream_video(
    file_id: int,
    direct_play: bool = False,
    range: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Streams video files. Natively streams MP4/WebM, and live-transcodes MKV."""

    file_path = await get_media_file_path(db, file_id)

    if not file_path:
        raise HTTPException(status_code=404, detail='Media file not found on disk')

    # ROUTE A: THE MKV TRANSCODER (FFMPEG)
    if file_path.lower().endswith('.mkv') and not direct_play:
        return StreamingResponse(
            generate_ffmpeg_stream(file_path), media_type='video/mp4'
        )

    # ROUTE B: NATIVE STREAMING (MP4 / WebM / Direct Play)
    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = 'application/octet-stream'

    # FileResponse automatically handles HTTP Range requests and Zero-Copy streaming
    return FileResponse(
        path=file_path,
        media_type=content_type,
    )
