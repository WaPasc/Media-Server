from pydantic import BaseModel


class ProgressUpdate(BaseModel):
    file_id: int
    current_time: float
    total_duration: float
