#!/usr/bin/env python
import PTN
import subprocess
import os
from dotenv import load_dotenv 

load_dotenv() # This loads variables from .env into os.environ 

TMDB_API_KEY = os.getenv("TMDB_KEY")


def get_file_technical_specs(file_path: str) -> str:
    cmd = [
        'ffprobe', 
        '-v', 'quiet', 
        '-print_format', 'json', 
        '-show_format', 
        '-show_streams', 
        file_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


def extract_local_info(file_path):
    """Combines PTN and ffprobe into a clean local object."""
    specs = get_file_technical_specs(file_path)
    filename_info = PTN.parse(os.path.basename(file_path))
    
    # ffprobe might have multiple streams; find the video one
    video_stream = next((s for s in specs['streams'] if s['codec_type'] == 'video'), specs['streams'][0])
    
    return {
        "title": filename_info.get('title', "Unknown"),
        "season": filename_info.get('season', 0),
        "episode": filename_info.get('episode', 0),
        "year": filename_info.get('year'),
        "duration": float(specs['format'].get('duration', 0)),
        "codec": video_stream.get('codec_name'),
        "resolution": f"{video_stream.get('width')}x{video_stream.get('height')}",
        "abs_path": os.path.abspath(file_path)
    }


