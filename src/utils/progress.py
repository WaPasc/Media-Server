from models.user import WatchProgress


def calculate_progress_percentage(progress: WatchProgress) -> float:
    media = progress.media_file

    if not media or not media.duration or media.duration <= 0:
        return 0.0

    return round((progress.stopped_at / media.duration) * 100, 2)
