from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Movie
from app.services.tmdb_client import TMDBClient


async def refresh_movie_metadata(db: AsyncSession, tmdb: TMDBClient, movie_id: int):
    movie = await db.get(Movie, movie_id)
    if not movie or not movie.tmdb_id:
        return None

    data = await tmdb.get_movie(movie.tmdb_id)

    movie.title = data.get('title', movie.title)
    movie.overview = data.get('overview', movie.overview)
    movie.poster_path = data.get('poster_path', movie.poster_path)
    movie.backdrop_path = data.get('backdrop_path', movie.backdrop_path)

    await db.commit()
    return movie


# async def refresh_show_metadata(db: AsyncSession, tmdb: TMDBClient, show_id: int):
#     show = await db.get(TVShow, show_id)
#     if not show or not show.tmdb_id:
#         return None

#     data = await tmdb.get_tv_show(show.tmdb_id)

#     show.title = data.get('name', show.title)
#     show.overview = data.get('overview', show.overview)
#     show.poster_path = data.get('poster_path', show.poster_path)
#     show.backdrop_path = data.get('backdrop_path', show.backdrop_path)


#     await db.commit()
#     return show
