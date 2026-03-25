from pydantic import BaseModel


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
