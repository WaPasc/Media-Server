from datetime import datetime
from zoneinfo import ZoneInfo


def get_brussels_time():
    """Returns a timezone-aware datetime for Brussels."""
    return datetime.now(ZoneInfo('Europe/Brussels'))
