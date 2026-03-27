from typing import Literal, Union

from pydantic import BaseModel

from app.schemas.movies import MovieResponse
from app.schemas.shows import EpisodeResponse, ShowResponse


class ProgressUpdate(BaseModel):
    file_id: int
    current_time: float
    total_duration: float


class ProgressUpdateResponse(BaseModel):
    status: str
    stopped_at: float
    is_completed: bool


class ProgressResponse(BaseModel):
    stopped_at: float


class ContinueWatchingBase(BaseModel):
    file_id: int
    stopped_at: float
    duration: float | None = None
    progress_percentage: float
    updated_at: str


class ContinueWatchingMovie(ContinueWatchingBase):
    type: Literal['movie'] = 'movie'
    movie: 'MovieResponse'


class ContinueWatchingEpisode(ContinueWatchingBase):
    type: Literal['episode'] = 'episode'
    show: 'ShowResponse'
    episode: 'EpisodeResponse'
    season_number: int


ContinueWatchingItem = Union[ContinueWatchingMovie, ContinueWatchingEpisode]
