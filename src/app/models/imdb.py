from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ImdbRating(Base):
    """IMDb rating ingested from the title.ratings.tsv.gz non-commercial
    dataset (https://datasets.imdbws.com/). Refreshed weekly.

    Keyed by tconst so we can look up ratings for movies/episodes by their
    cached imdb_id without joining on a foreign key, IMDb has ~1.5M
    titles and we only join against the small subset whose tconst matches
    something in our library.
    """

    __tablename__ = 'imdb_ratings'

    tconst: Mapped[str] = mapped_column(String(20), primary_key=True)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[Optional[int]] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
