import json
import logging

from botocore.exceptions import ClientError

from app.core.s3 import s3_client

logger = logging.getLogger(__name__)


async def ensure_bucket_exists(bucket_name: str):
    """
    Ensures the specified bucket exists, creating it if necessary.
    """
    if not bucket_name:
        logger.warning('No bucket name provided to ensure_bucket_exists.')
        return

    async with s3_client.get_client() as s3:
        try:
            await s3.head_bucket(Bucket=bucket_name)
            logger.info(f"Bucket '{bucket_name}' already exists.")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code in ('404', 'NoSuchBucket'):
                logger.info(f"Bucket '{bucket_name}' not found. Creating...")
                await s3.create_bucket(Bucket=bucket_name)
                logger.info(f"Bucket '{bucket_name}' created successfully.")
            else:
                logger.error(f'Error checking bucket {bucket_name}: {e}')
                raise


async def apply_public_read_policy(bucket_name: str):
    """
    Applies a strict public read policy to the specified bucket.
    Allows anonymous GetObject and GetBucketLocation — NO ListBucket.
    """
    if not bucket_name:
        logger.warning('No bucket name provided to apply_public_read_policy.')
        return

    policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Sid': 'PublicReadBucketLocation',
                'Effect': 'Allow',
                'Principal': '*',
                'Action': ['s3:GetBucketLocation'],
                'Resource': [f'arn:aws:s3:::{bucket_name}'],
            },
            {
                'Sid': 'PublicReadGetObject',
                'Effect': 'Allow',
                'Principal': '*',
                'Action': ['s3:GetObject'],
                'Resource': [f'arn:aws:s3:::{bucket_name}/*'],
            },
        ],
    }

    async with s3_client.get_client() as s3:
        try:
            await s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
            logger.info(f"Public read policy applied to '{bucket_name}'.")
        except ClientError as e:
            logger.error(f'Failed to apply bucket policy to {bucket_name}: {e}')
            raise
