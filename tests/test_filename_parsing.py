from unittest.mock import AsyncMock

import PTN
import pytest

from app.services.scanner_service import (
    _coerce_non_negative_int,
    _coerce_positive_int,
    _find_best_tmdb_match_show,
    _normalize_title,
)
from app.utils.metadata import extract_local_info

EMPTY_SPECS = {'streams': [], 'format': {}}


# ---------------------------------------------------------------------------
# PTN — movie filenames
# ---------------------------------------------------------------------------


class TestMovieFilenameParsing:
    def test_extracts_title_and_year(self):
        result = PTN.parse('The.Matrix.1999.1080p.mkv')
        assert result['title'] == 'The Matrix'
        assert result['year'] == 1999

    def test_extracts_title_without_year(self):
        result = PTN.parse('Inception.BluRay.1080p.mkv')
        assert result['title'] == 'Inception'
        assert result.get('year') is None

    def test_no_season_or_episode_in_movie(self):
        result = PTN.parse('The.Matrix.1999.1080p.mkv')
        assert result.get('season') is None
        assert result.get('episode') is None

    def test_title_with_spaces_in_name(self):
        result = PTN.parse('The Dark Knight 2008 BluRay.mkv')
        assert result['title'] == 'The Dark Knight'
        assert result['year'] == 2008


# ---------------------------------------------------------------------------
# PTN — episode filenames
# ---------------------------------------------------------------------------


class TestEpisodeFilenameParsing:
    def test_extracts_show_title_season_episode(self):
        result = PTN.parse('Breaking.Bad.S01E01.720p.mkv')
        assert result['title'] == 'Breaking Bad'
        assert result['season'] == 1
        assert result['episode'] == 1

    def test_double_digit_season_and_episode(self):
        result = PTN.parse('Breaking.Bad.S05E16.mkv')
        assert result['season'] == 5
        assert result['episode'] == 16

    def test_show_with_year_in_filename(self):
        result = PTN.parse('Game.of.Thrones.2011.S03E09.mkv')
        assert result['title'] == 'Game of Thrones'
        assert result['season'] == 3
        assert result['episode'] == 9


# ---------------------------------------------------------------------------
# _coerce_positive_int
# ---------------------------------------------------------------------------


class TestCoercePositiveInt:
    def test_valid_positive_integer(self):
        assert _coerce_positive_int(5) == 5

    def test_zero_returns_none(self):
        assert _coerce_positive_int(0) is None

    def test_negative_returns_none(self):
        assert _coerce_positive_int(-1) is None

    def test_none_returns_none(self):
        assert _coerce_positive_int(None) is None

    def test_string_digit_is_parsed(self):
        assert _coerce_positive_int('3') == 3

    def test_invalid_string_returns_none(self):
        assert _coerce_positive_int('abc') is None

    def test_list_uses_first_element(self):
        assert _coerce_positive_int([2, 5]) == 2

    def test_empty_list_returns_none(self):
        assert _coerce_positive_int([]) is None


# ---------------------------------------------------------------------------
# _coerce_non_negative_int
# ---------------------------------------------------------------------------


class TestCoerceNonNegativeInt:
    def test_zero_is_valid(self):
        assert _coerce_non_negative_int(0) == 0

    def test_positive_is_valid(self):
        assert _coerce_non_negative_int(3) == 3

    def test_negative_returns_none(self):
        assert _coerce_non_negative_int(-1) is None

    def test_none_returns_none(self):
        assert _coerce_non_negative_int(None) is None


# ---------------------------------------------------------------------------
# _normalize_title
# ---------------------------------------------------------------------------


class TestNormalizeTitle:
    def test_lowercases(self):
        assert _normalize_title('Breaking Bad') == 'breaking bad'

    def test_strips_whitespace(self):
        assert _normalize_title('  Breaking Bad  ') == 'breaking bad'

    def test_collapses_internal_spaces(self):
        assert _normalize_title('Breaking  Bad') == 'breaking bad'


# ---------------------------------------------------------------------------
# _find_best_tmdb_match_show
# ---------------------------------------------------------------------------


class TestFindBestTmdbMatchShow:
    def test_strict_match_on_title_and_year(self):
        results = [
            {'id': 1, 'name': 'Breaking Bad', 'first_air_date': '2008-01-01'},
            {'id': 2, 'name': 'Breaking Bad', 'first_air_date': '2020-01-01'},
        ]
        match = _find_best_tmdb_match_show(results, 'breaking bad', 2008, 'Breaking Bad')
        assert match['id'] == 1

    def test_loose_match_when_no_year(self):
        results = [
            {'id': 99, 'name': 'Some Other Show', 'first_air_date': '2010-01-01'},
            {'id': 1, 'name': 'Breaking Bad', 'first_air_date': '2008-01-01'},
        ]
        match = _find_best_tmdb_match_show(results, 'breaking bad', None, 'Breaking Bad')
        assert match['id'] == 1

    def test_fallback_to_first_result(self):
        results = [
            {'id': 42, 'name': 'Something Unrelated', 'first_air_date': ''},
        ]
        match = _find_best_tmdb_match_show(results, 'breaking bad', 2008, 'Breaking Bad')
        assert match['id'] == 42


# ---------------------------------------------------------------------------
# extract_local_info — ffprobe mocked out
# ---------------------------------------------------------------------------


class TestExtractLocalInfo:
    async def test_movie_filename(self, tmp_path, mocker):
        fake_file = tmp_path / 'The.Matrix.1999.1080p.mkv'
        fake_file.touch()
        mocker.patch('app.utils.metadata.get_file_technical_specs', new=AsyncMock(return_value=EMPTY_SPECS))

        result = await extract_local_info(fake_file)

        assert result['title'] == 'The Matrix'
        assert result['year'] == 1999
        assert result['season'] == 0
        assert result['episode'] == 0

    async def test_episode_filename(self, tmp_path, mocker):
        fake_file = tmp_path / 'Breaking.Bad.S01E01.720p.mkv'
        fake_file.touch()
        mocker.patch('app.utils.metadata.get_file_technical_specs', new=AsyncMock(return_value=EMPTY_SPECS))

        result = await extract_local_info(fake_file)

        assert result['title'] == 'Breaking Bad'
        assert result['season'] == 1
        assert result['episode'] == 1

    async def test_missing_video_stream_gives_no_resolution(self, tmp_path, mocker):
        fake_file = tmp_path / 'The.Matrix.1999.mkv'
        fake_file.touch()
        mocker.patch('app.utils.metadata.get_file_technical_specs', new=AsyncMock(return_value=EMPTY_SPECS))

        result = await extract_local_info(fake_file)

        assert result['resolution'] is None
        assert result['codec'] is None

    @pytest.mark.parametrize('filename,expected_title,expected_season,expected_episode', [
        ('Suits.S01E01.720p.mkv',              'Suits',            1, 1),
        ('Game.of.Thrones.S03E09.1080p.mkv',   'Game of Thrones',  3, 9),
        ('The.100.S02E03.mkv',                 'The 100',          2, 3),
        ('Peaky.Blinders.S05E06.mkv',          'Peaky Blinders',   5, 6),
        ('Breaking.Bad.S04E11.mkv',            'Breaking Bad',     4, 11),
        ('The.Wire.S02E01.mkv',                'The Wire',         2, 1),
        ('Stranger.Things.S03E04.mkv',         'Stranger Things',  3, 4),
        ('House.of.Cards.S02E05.mkv',          'House of Cards',   2, 5),
        ('Better.Call.Saul.S06E13.mkv',        'Better Call Saul', 6, 13),
        ('The.Crown.S04E07.mkv',               'The Crown',        4, 7),
    ])
    async def test_show_filenames(self, tmp_path, mocker, filename, expected_title, expected_season, expected_episode):
        fake_file = tmp_path / filename
        fake_file.touch()
        mocker.patch('app.utils.metadata.get_file_technical_specs', new=AsyncMock(return_value=EMPTY_SPECS))

        result = await extract_local_info(fake_file)

        assert result['title'] == expected_title
        assert result['season'] == expected_season
        assert result['episode'] == expected_episode

    @pytest.mark.parametrize('filename,expected_title,expected_year', [
        ('Oppenheimer.2023.1080p.mkv',            'Oppenheimer',              2023),
        ('War.Machine.2017.mkv',                  'War Machine',              2017),
        ('The.Dark.Knight.2008.BluRay.mkv',       'The Dark Knight',          2008),
        ('Inception.2010.1080p.mkv',              'Inception',                2010),
        ('Interstellar.2014.mkv',                 'Interstellar',             2014),
        ('The.Godfather.1972.mkv',                'The Godfather',            1972),
        ('Pulp.Fiction.1994.mkv',                 'Pulp Fiction',             1994),
        ('The.Shawshank.Redemption.1994.mkv',     'The Shawshank Redemption', 1994),
        ('Goodfellas.1990.mkv',                   'Goodfellas',               1990),
        ('Parasite.2019.mkv',                     'Parasite',                 2019),
    ])
    async def test_movie_filenames(self, tmp_path, mocker, filename, expected_title, expected_year):
        fake_file = tmp_path / filename
        fake_file.touch()
        mocker.patch('app.utils.metadata.get_file_technical_specs', new=AsyncMock(return_value=EMPTY_SPECS))

        result = await extract_local_info(fake_file)

        assert result['title'] == expected_title
        assert result['year'] == expected_year
