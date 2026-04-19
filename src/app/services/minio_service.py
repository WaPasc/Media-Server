import logging

import httpx
from botocore.exceptions import ClientError

from app.core.s3 import s3_client

logger = logging.getLogger(__name__)


async def ensure_image_in_minio(tmdb_path: str, size: str = 'original') -> str | None:
    """
    Ensures a TMDB image exists in the local MinIO bucket.
    If it doesn't exist, downloads it from TMDB and uploads it.
    Returns the local public URL.
    """
    if not tmdb_path:
        return None

    # The S3 key shouldn't have a leading slash
    s3_key = tmdb_path.lstrip('/')
    bucket = s3_client.images_bucket

    async with s3_client.get_client() as s3:
        # 1. Check if the image already exists in MinIO
        try:
            await s3.head_object(Bucket=bucket, Key=s3_key)
            logger.debug(f'Image already in MinIO: {s3_key}')
            return s3_client.build_public_url(s3_key)
        except ClientError as e:
            # If the error is a 404 Not Found, we need to download it.
            # Otherwise, re-raise the exception.
            error_code = e.response.get('Error', {}).get('Code')
            if error_code != '404':
                logger.error(f'Error checking MinIO for {s3_key}: {e}')
                raise

        # 2. Image not found in MinIO, download from TMDB
        tmdb_url = f'https://image.tmdb.org/t/p/{size}/{s3_key}'
        logger.info(f'Downloading missing image from TMDB: {tmdb_url}')

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(tmdb_url)

            if response.status_code != 200:
                logger.warning(
                    f'Failed to download image from TMDB (Status {response.status_code}): {tmdb_url}'
                )
                return None

            content_type = response.headers.get('Content-Type', 'image/jpeg')
            image_data = response.content

        # 3. Upload to MinIO
        try:
            await s3.put_object(
                Bucket=bucket, Key=s3_key, Body=image_data, ContentType=content_type
            )
            logger.info(f'Successfully uploaded to MinIO: {s3_key}')
            return s3_client.build_public_url(s3_key)
        except Exception as e:
            logger.error(f'Failed to upload image to MinIO: {e}')
            return None
