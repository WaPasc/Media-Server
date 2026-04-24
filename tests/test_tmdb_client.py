from unittest.mock import AsyncMock

import httpx
import pytest
from pytest_mock import MockerFixture

from app.services.tmdb_client import TMDBClient

MOCK_CONFIG = {
    'images': {
        'secure_base_url': 'https://image.tmdb.org/t/p/',
        'poster_sizes': ['w342', 'w500', 'original'],
        'backdrop_sizes': ['w780', 'w1280', 'original'],
    }
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('TMDB_READ_ACCESS', 'fake-token')
    return TMDBClient()


# ---------------------------------------------------------------------------
# _load_configuration - network failures must not crash the server
# ---------------------------------------------------------------------------


class TestLoadConfiguration:
    async def test_connect_error_is_swallowed(
        self, client: TMDBClient, mocker: MockerFixture
    ):
        mocker.patch.object(
            client, '_get_configuration', side_effect=httpx.ConnectError('no network')
        )

        await client._load_configuration()

        assert client.config is None
        assert client.image_base_url is None

    async def test_timeout_is_swallowed(
        self, client: TMDBClient, mocker: MockerFixture
    ):
        mocker.patch.object(
            client,
            '_get_configuration',
            side_effect=httpx.TimeoutException('timed out'),
        )

        await client._load_configuration()

        assert client.config is None
        assert client.image_base_url is None

    async def test_successful_load_populates_fields(
        self, client: TMDBClient, mocker: MockerFixture
    ):
        mocker.patch.object(
            client, '_get_configuration', new=AsyncMock(return_value=MOCK_CONFIG)
        )

        await client._load_configuration()

        assert client.image_base_url == 'https://image.tmdb.org/t/p/'
        assert client.poster_sizes == ['w342', 'w500', 'original']
        assert client.backdrop_sizes == ['w780', 'w1280', 'original']


# ---------------------------------------------------------------------------
# create() - must return a client even when offline
# ---------------------------------------------------------------------------


class TestCreate:
    async def test_create_succeeds_when_offline(
        self, monkeypatch, mocker: MockerFixture
    ):
        monkeypatch.setenv('TMDB_READ_ACCESS', 'fake-token')
        mocker.patch(
            'app.services.tmdb_client.TMDBClient._get_configuration',
            side_effect=httpx.ConnectError('no network'),
        )

        client = await TMDBClient.create()

        assert client is not None
        assert client.config is None
        await client.close()

    async def test_create_fully_configured_when_online(
        self, monkeypatch, mocker: MockerFixture
    ):
        monkeypatch.setenv('TMDB_READ_ACCESS', 'fake-token')
        mocker.patch(
            'app.services.tmdb_client.TMDBClient._get_configuration',
            new=AsyncMock(return_value=MOCK_CONFIG),
        )

        client = await TMDBClient.create()

        assert client.image_base_url == 'https://image.tmdb.org/t/p/'
        await client.close()


# ---------------------------------------------------------------------------
# Image URL methods - must return None when config is not loaded
# ---------------------------------------------------------------------------


class TestImageUrls:
    def test_build_image_url_returns_none_when_not_configured(self, client: TMDBClient):
        assert client.build_image_url('/poster.jpg') is None

    def test_get_poster_url_returns_none_when_not_configured(self, client: TMDBClient):
        assert client.get_poster_url('/poster.jpg') is None

    def test_get_backdrop_url_returns_none_when_not_configured(
        self, client: TMDBClient
    ):
        assert client.get_backdrop_url('/backdrop.jpg') is None

    def test_get_still_url_returns_none_when_not_configured(self, client: TMDBClient):
        assert client.get_still_url('/still.jpg') is None

    def test_build_image_url_returns_none_for_empty_path(self, client: TMDBClient):
        client.image_base_url = 'https://image.tmdb.org/t/p/'
        assert client.build_image_url('') is None
        assert client.build_image_url(None) is None

    def test_build_image_url_returns_correct_url_when_configured(
        self, client: TMDBClient
    ):
        client.image_base_url = 'https://image.tmdb.org/t/p/'
        assert (
            client.build_image_url('/poster.jpg', 'w500')
            == 'https://image.tmdb.org/t/p/w500/poster.jpg'
        )

    def test_get_poster_url_uses_default_size(self, client: TMDBClient):
        client.image_base_url = 'https://image.tmdb.org/t/p/'
        assert (
            client.get_poster_url('/poster.jpg')
            == 'https://image.tmdb.org/t/p/w342/poster.jpg'
        )

    def test_get_backdrop_url_uses_default_size(self, client: TMDBClient):
        client.image_base_url = 'https://image.tmdb.org/t/p/'
        assert (
            client.get_backdrop_url('/backdrop.jpg')
            == 'https://image.tmdb.org/t/p/w780/backdrop.jpg'
        )


# ---------------------------------------------------------------------------
# ensure_configured() - lazy retry behaviour
# ---------------------------------------------------------------------------


class TestEnsureConfigured:
    async def test_retries_after_initial_failure(
        self, client: TMDBClient, mocker: MockerFixture
    ):
        mocker.patch.object(
            client, '_get_configuration', side_effect=httpx.ConnectError('offline')
        )
        await client._load_configuration()
        assert client.config is None

        mocker.patch.object(
            client, '_get_configuration', new=AsyncMock(return_value=MOCK_CONFIG)
        )
        await client.ensure_configured()

        assert client.image_base_url == 'https://image.tmdb.org/t/p/'

    async def test_skips_network_call_when_already_configured(
        self, client: TMDBClient, mocker: MockerFixture
    ):
        mock_get = AsyncMock(return_value=MOCK_CONFIG)
        mocker.patch.object(client, '_get_configuration', new=mock_get)

        await client.ensure_configured()
        await client.ensure_configured()

        assert mock_get.call_count == 1
