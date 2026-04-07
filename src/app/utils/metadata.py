#!/usr/bin/env python
import asyncio
import json
import logging
import os
from pathlib import Path

import PTN
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv('TMDB_KEY')

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def get_file_technical_specs(file_path: Path) -> dict:
    proc = await asyncio.create_subprocess_exec(
        'ffprobe',
        '-v',
        'quiet',
        '-print_format',
        'json',
        '-show_format',
        '-show_streams',
        str(file_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.warning(
            f'ffprobe exited with code {proc.returncode} for {file_path}: '
            f'{stderr.decode(errors="replace").strip()}'
        )

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {'streams': [], 'format': {}}


async def extract_local_info(file_path: Path) -> dict:
    """Combines PTN and ffprobe into a clean local object."""
    specs = await get_file_technical_specs(file_path)
    filename_info = PTN.parse(
        file_path.name
    )  # use Path.name instead of os.path.basename

    streams = specs.get('streams', [])
    video_stream = next(
        (s for s in streams if s.get('codec_type') == 'video'),
        streams[0] if streams else {},
    )

    width, height = video_stream.get('width'), video_stream.get('height')

    return {
        'title': filename_info.get('title', 'Unknown'),
        'season': filename_info.get('season', 0),
        'episode': filename_info.get('episode', 0),
        'year': filename_info.get('year'),
        'duration': float(specs.get('format', {}).get('duration', 0)),
        'codec': video_stream.get('codec_name'),
        'resolution': f'{width}x{height}' if width and height else None,
        'abs_path': str(
            file_path.resolve()
        ),  # use Path.resolve() instead of os.path.abspath
    }


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('Usage: python scanner.py /path/to/movie')
    else:
        metadata = asyncio.run(extract_local_info(Path(sys.argv[1])))
        print(metadata)
