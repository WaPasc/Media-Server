import os
import requests
from dotenv import load_dotenv

load_dotenv()


class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self):
        self.read_token = os.getenv("TMDB_READ_ACCESS")
        if not self.read_token:
            raise ValueError("TMDB_READ_ACCESS not found in environment")

        # Persistent HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.read_token}",
            "accept": "application/json"
        })

        # Cache configuration
        self.config = self._get_configuration()

        self.image_base_url = self.config["images"]["secure_base_url"]
        self.poster_sizes = self.config["images"]["poster_sizes"]
        self.backdrop_sizes = self.config["images"]["backdrop_sizes"]

    # -----------------------------
    # Internal request helper
    # -----------------------------

    def _get(self, endpoint, params=None):
        url = f"{self.BASE_URL}{endpoint}"
        response = self.session.get(url, params=params)

        response.raise_for_status()

        return response.json()

    # -----------------------------
    # Configuration
    # -----------------------------

    def _get_configuration(self):
        return self._get("/configuration")

    # -----------------------------
    # Movies
    # -----------------------------

    def get_movie(self, movie_id):
        return self._get(f"/movie/{movie_id}")

    def search_movie(self, query, page=1):
        params = {
            "query": query,
            "page": page
        }
        return self._get("/search/movie", params)

    def get_movie_credits(self, movie_id):
        return self._get(f"/movie/{movie_id}/credits")
    
    # -----------------------------
    # TV shows
    # -----------------------------

    def get_tv_show(self, tv_show_id):
        return self._get(f"/tv/{tv_show_id}")
    
    def search_tv_show(self, query, page=1):
        params = {
            "query": query,
            "page": page
        }
        return self._get("/search/tv", params)
    
    def get_tv_show_credits(self, tv_show_id):
        return self._get(f"/tv/{tv_show_id}/credits")

    # -----------------------------
    # Discover
    # -----------------------------

    def discover_movies(self, page=1):
        params = {"page": page}
        return self._get("/discover/movie", params)
    
    def discover_tv_shows(self, page=1):
        params = {"page": page}
        return self._get("/discover/tv", params)

    # -----------------------------
    # Images
    # -----------------------------

    def build_image_url(self, path, size="w500"):
        if not path:
            return None
        return f"{self.image_base_url}{size}{path}"

    def get_poster_url(self, path, size="w342"):
        return self.build_image_url(path, size)

    def get_backdrop_url(self, path, size="w780"):
        return self.build_image_url(path, size)