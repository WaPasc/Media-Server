from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ScanDirectoryBase(BaseModel):
    path: str = Field(..., description='The path to the directory to scan.')
    media_type: str = Field(..., description="'movies' or 'shows'")


class ScanDirectoryCreate(ScanDirectoryBase):
    pass


class ScanDirectoryResponse(ScanDirectoryBase):
    id: int
    last_scanned: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScanAvailabilityResponse(BaseModel):
    status: str
    message: str
