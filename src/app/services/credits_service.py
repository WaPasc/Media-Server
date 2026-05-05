import asyncio
import logging

import httpx
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.media import Credit, Person
from app.services.minio_service import ensure_image_in_minio
from app.services.tmdb_client import TMDBClient

logger = logging.getLogger(__name__)

# Profile image size mirrored to MinIO. h632 is the largest non-original
# offering and renders at full quality on the desktop detail strip.
TMDB_PROFILE_SIZE = 'h632'


async def _upsert_person(
    session: AsyncSession, p_data: dict, background_tasks: set
) -> Person | None:
    """Upsert a Person row keyed on TMDB id. Queues a profile-image mirror
    task on the background_tasks set so the caller can await them later.
    """
    tmdb_id = p_data.get('id')
    if tmdb_id is None:
        return None

    stmt = select(Person).where(Person.tmdb_id == tmdb_id)
    person = (await session.execute(stmt)).scalars().first()

    new_name = p_data.get('name') or ''
    new_path = p_data.get('profile_path')

    if person is None:
        person = Person(tmdb_id=tmdb_id, name=new_name, profile_path=new_path)
        session.add(person)
        await session.flush()
    else:
        if new_name and new_name != person.name:
            person.name = new_name
        if new_path and new_path != person.profile_path:
            person.profile_path = new_path

    if person.profile_path:
        task = asyncio.create_task(
            ensure_image_in_minio(person.profile_path, TMDB_PROFILE_SIZE)
        )
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    return person


def _show_character(cast_item: dict) -> str | None:
    """aggregate_credits exposes a `roles` array instead of a single
    `character` field. Pick the role with the highest episode_count, that
    is the headline character to display.
    """
    roles = cast_item.get('roles') or []
    if not roles:
        return None
    best = max(roles, key=lambda r: r.get('episode_count') or 0)
    return best.get('character')


async def _replace_credits(
    session: AsyncSession,
    *,
    target_field: str,
    target_id: int,
    tmdb_cast: list[dict],
    background_tasks: set,
    show_credit: bool = False,
) -> None:
    """Wipe and rewrite credits for one (movie | show | episode). Wholesale
    replace is simpler than diffing and avoids stale rows when TMDB drops
    or reorders cast entries between scans.
    """
    await session.execute(
        delete(Credit).where(getattr(Credit, target_field) == target_id)
    )

    for item in tmdb_cast:
        person = await _upsert_person(session, item, background_tasks)
        if person is None:
            continue

        if show_credit:
            character = _show_character(item)
            episode_count = item.get('total_episode_count')
        else:
            character = item.get('character')
            episode_count = None

        credit = Credit(
            person_id=person.id,
            character=character,
            cast_order=item.get('order'),
            episode_count=episode_count,
            **{target_field: target_id},
        )
        session.add(credit)

    await session.flush()


async def sync_movie_credits(
    session: AsyncSession,
    tmdb: TMDBClient,
    movie_id: int,
    movie_tmdb_id: int,
    background_tasks: set,
) -> None:
    try:
        payload = await tmdb.get_movie_credits(movie_tmdb_id)
    except httpx.HTTPError as e:
        logger.warning('movie credits fetch failed (tmdb=%s): %s', movie_tmdb_id, e)
        return

    await _replace_credits(
        session,
        target_field='movie_id',
        target_id=movie_id,
        tmdb_cast=payload.get('cast') or [],
        background_tasks=background_tasks,
    )


async def sync_show_credits(
    session: AsyncSession,
    tmdb: TMDBClient,
    show_id: int,
    show_tmdb_id: int,
    background_tasks: set,
) -> None:
    try:
        payload = await tmdb.get_tv_show_aggregate_credits(show_tmdb_id)
    except httpx.HTTPError as e:
        logger.warning('show credits fetch failed (tmdb=%s): %s', show_tmdb_id, e)
        return

    await _replace_credits(
        session,
        target_field='show_id',
        target_id=show_id,
        tmdb_cast=payload.get('cast') or [],
        background_tasks=background_tasks,
        show_credit=True,
    )


async def sync_episode_credits(
    session: AsyncSession,
    tmdb: TMDBClient,
    episode_id: int,
    show_tmdb_id: int,
    season_number: int,
    episode_number: int,
    background_tasks: set,
) -> None:
    """Stores guest stars only. Show regulars stay on the show row, the API
    merges them at read time so we don't duplicate every regular on every
    episode of a long-running show.
    """
    try:
        payload = await tmdb.get_tv_episode_credits(
            show_tmdb_id, season_number, episode_number
        )
    except httpx.HTTPError as e:
        logger.warning(
            'episode credits fetch failed (tmdb=%s S%sE%s): %s',
            show_tmdb_id,
            season_number,
            episode_number,
            e,
        )
        return

    await _replace_credits(
        session,
        target_field='episode_id',
        target_id=episode_id,
        tmdb_cast=payload.get('guest_stars') or [],
        background_tasks=background_tasks,
    )
