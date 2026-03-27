from app.models.user import WatchProgress


def calculate_progress_percentage(progress: WatchProgress) -> float:
    media = progress.media_file

    if not media or not media.duration or media.duration <= 0:
        return 0.0

    return round((progress.stopped_at / media.duration) * 100, 2)


def check_is_completed(
    current_time: float, total_duration: float, threshold: float = 0.95
) -> bool:
    """Calculates if the user has watched enough of the video to mark it as completed."""
    if total_duration <= 0:
        return False
    return (current_time / total_duration) >= threshold
