def calculate_progress_percentage(
    stopped_at: float, duration: float | None
) -> float:
    if not duration or duration <= 0:
        return 0.0

    return round((stopped_at / duration) * 100, 2)


def check_is_completed(
    current_time: float, total_duration: float, threshold: float = 0.95
) -> bool:
    """Calculates if the user has watched enough of the video to mark it as completed."""
    if total_duration <= 0:
        return False
    return (current_time / total_duration) >= threshold
