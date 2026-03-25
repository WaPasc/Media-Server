import asyncio
import mimetypes
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from models.media import MediaFile

router = APIRouter(prefix='/api', tags=['stream'])


@router.get('/stream/{file_id}')
async def stream_video(
    file_id: int,
    direct_play: bool = False,
    range: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Streams video files. Natively streams MP4/WebM, and live-transcodes MKV."""
    stmt = Select(MediaFile).where(MediaFile.id == file_id)
    result = await db.execute(stmt)
    media_file = result.scalars().first()

    if not media_file or not os.path.exists(media_file.file_path):
        raise HTTPException(status_code=404, detail='Media file not found on disk')

    file_path = media_file.file_path

    # ==========================================
    # ROUTE A: THE MKV TRANSCODER (FFMPEG)
    # ==========================================
    if file_path.lower().endswith('.mkv') and not direct_play:

        async def ffmpeg_streamer():
            # The Magic Command:
            # -c:v libx264 -preset ultrafast: Encodes video extremely fast
            # -c:a aac: Converts audio to web-safe AAC
            # -movflags frag_keyframe+empty_moov: Crucial! Allows MP4 to stream before it's finished
            command = [
                'ffmpeg',
                '-i',
                file_path,
                '-c:v',
                'libx264',
                '-preset',
                'faster',  # Slower than ultrafast, but much better quality
                '-crf',
                '18',  # <--- Visually lossless quality (18-22 is the golden range)
                '-c:a',
                'aac',
                '-b:a',
                '320k',  # <--- Cinematic audio
                '-movflags',
                'frag_keyframe+empty_moov+faststart',
                '-f',
                'mp4',
                '-',
            ]

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,  # Hides FFmpeg logs from your terminal
            )

            try:
                while True:
                    # Read in 1MB chunks from FFmpeg's output
                    chunk = await process.stdout.read(1024 * 1024)
                    if not chunk:
                        break
                    yield chunk
            finally:
                # If the user closes the browser or clicks "Stop Playback", kill FFmpeg!
                if process.returncode is None:
                    process.kill()

        # Return the live stream. Status 200 (OK) because we aren't handling byte ranges for live transcodes yet.
        return StreamingResponse(ffmpeg_streamer(), media_type='video/mp4')

    # ==========================================
    # ROUTE B: NATIVE STREAMING (MP4 / WebM)
    # ==========================================
    # Simple mime-type guess based on extension
    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = 'application/octet-stream'

    # FileResponse automatically handles HTTP Range requests, 206 Partial Content,
    # and zero-copy os.sendfile streaming
    return FileResponse(
        path=file_path,
        media_type=content_type,
    )
