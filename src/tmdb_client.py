import os

import httpx
from dotenv import load_dotenv

load_dotenv()


class TMDBClient:
    BASE_URL = 'https://api.themoviedb.org/3'

    def __init__(self, timeout=10.0):
        self.read_token = os.getenv('TMDB_READ_ACCESS')
        if not self.read_token:
            raise ValueError('TMDB_READ_ACCESS not found in environment')

        # Persistent async HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=timeout,
            headers={
                'Authorization': f'Bearer {self.read_token}',
                'accept': 'application/json',
            },
        )

        # Loaded asynchronously through `create` or `__aenter__`
        self.config = None
        self.image_base_url = None
        self.poster_sizes = []
        self.backdrop_sizes = []

    @classmethod
    async def create(cls, timeout=10.0):
        instance = cls(timeout=timeout)
        await instance._load_configuration()
        return instance

    async def __aenter__(self):
        if self.config is None:
            await self._load_configuration()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self):
        await self.client.aclose()

    # -----------------------------
    # Internal request helper
    # -----------------------------

    async def _get(self, endpoint, params=None):
        response = await self.client.get(endpoint, params=params)

        response.raise_for_status()

        return response.json()

    # -----------------------------
    # Configuration
    # -----------------------------

    async def _get_configuration(self):
        return await self._get('/configuration')

    async def _load_configuration(self):
        self.config = await self._get_configuration()
        self.image_base_url = self.config['images']['secure_base_url']
        self.poster_sizes = self.config['images']['poster_sizes']
        self.backdrop_sizes = self.config['images']['backdrop_sizes']

    # -----------------------------
    # Movies
    # -----------------------------

    async def get_movie(self, movie_id):
        return await self._get(f'/movie/{movie_id}')

    async def search_movie(self, query, page=1):
        params = {'query': query, 'page': page}
        return await self._get('/search/movie', params)

    async def get_movie_credits(self, movie_id):
        return await self._get(f'/movie/{movie_id}/credits')

    # -----------------------------
    # TV shows
    # -----------------------------

    async def get_tv_show(self, tv_show_id):
        return await self._get(f'/tv/{tv_show_id}')

    async def search_tv_show(self, query, page=1):
        params = {'query': query, 'page': page}
        return await self._get('/search/tv', params)

    async def get_tv_show_credits(self, tv_show_id):
        return await self._get(f'/tv/{tv_show_id}/credits')

    # -----------------------------
    # Discover
    # -----------------------------

    async def discover_movies(self, page=1):
        params = {'page': page}
        return await self._get('/discover/movie', params)

    async def discover_tv_shows(self, page=1):
        params = {'page': page}
        return await self._get('/discover/tv', params)

    # -----------------------------
    # Images
    # -----------------------------

    def build_image_url(self, path, size='w500'):
        if not path:
            return None
        if not self.image_base_url:
            raise RuntimeError(
                'TMDB configuration is not loaded. Use `await TMDBClient.create()` first.'
            )
        return f'{self.image_base_url}{size}{path}'

    def get_poster_url(self, path, size='w342'):
        return self.build_image_url(path, size)

    def get_backdrop_url(self, path, size='w780'):
        return self.build_image_url(path, size)
