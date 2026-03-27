import asyncio
from typing import AsyncGenerator


async def generate_ffmpeg_stream(
    file_path: str, chunk_size: int = 1024 * 1024
) -> AsyncGenerator[bytes, None]:
    """Spawns an FFmpeg process to transcode video on the fly and yields byte chunks."""

    command = [
        'ffmpeg',
        '-i',
        file_path,
        '-c:v',
        'libx264',
        '-preset',
        'faster',
        '-crf',
        '18',
        '-c:a',
        'aac',
        '-b:a',
        '320k',
        '-movflags',
        'frag_keyframe+empty_moov+faststart',
        '-f',
        'mp4',
        '-',
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    try:
        while True:
            chunk = await process.stdout.read(chunk_size)
            if not chunk:
                break
            yield chunk
    finally:
        # cleanup: kill FFmpeg if the client disconnects
        if process.returncode is None:
            process.kill()
