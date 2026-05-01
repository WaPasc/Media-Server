import json
import uuid

import pytest
from botocore.exceptions import ClientError

from app.core.s3 import s3_client
from app.utils.s3_utils import apply_public_read_policy, ensure_bucket_exists

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def s3():
    async with s3_client.get_client() as client:
        yield client


async def _cleanup_bucket(s3, bucket: str) -> None:
    """Delete all objects in a bucket and then the bucket itself."""
    paginator = s3.get_paginator('list_objects_v2')
    async for page in paginator.paginate(Bucket=bucket):
        if 'Contents' in page:
            await s3.delete_objects(
                Bucket=bucket,
                Delete={'Objects': [{'Key': obj['Key']} for obj in page['Contents']]},
            )
    await s3.delete_bucket(Bucket=bucket)


@pytest.fixture
async def bucket_name():
    """Provide a unique bucket name. Test is responsible for creating it."""
    return f'test-bucket-{uuid.uuid4().hex[:8]}'


@pytest.fixture
async def test_bucket(s3, bucket_name):
    """Create a bucket and clean it up after the test."""
    await s3.create_bucket(Bucket=bucket_name)
    try:
        yield bucket_name
    finally:
        await _cleanup_bucket(s3, bucket_name)


@pytest.fixture
async def managed_bucket(s3, bucket_name):
    """Provide a bucket name and clean it up after the test (test creates it)."""
    try:
        yield bucket_name
    finally:
        await _cleanup_bucket(s3, bucket_name)


async def test_ensure_bucket_exists_creates_bucket(s3, managed_bucket):
    await ensure_bucket_exists(managed_bucket)

    response = await s3.head_bucket(Bucket=managed_bucket)
    assert response['ResponseMetadata']['HTTPStatusCode'] == 200


async def test_ensure_bucket_exists_is_idempotent(s3, managed_bucket):
    await ensure_bucket_exists(managed_bucket)
    await ensure_bucket_exists(managed_bucket)  # should not raise

    response = await s3.head_bucket(Bucket=managed_bucket)
    assert response['ResponseMetadata']['HTTPStatusCode'] == 200


async def test_apply_public_read_policy_sets_correct_statements(s3, test_bucket):
    await apply_public_read_policy(test_bucket)

    policy_response = await s3.get_bucket_policy(Bucket=test_bucket)
    policy = json.loads(policy_response['Policy'])
    statements = policy.get('Statement', [])

    assert len(statements) == 2, 'Policy should have exactly 2 statements.'

    # Statement 0: GetBucketLocation
    stmt_location = statements[0]
    assert stmt_location['Sid'] == 'PublicReadBucketLocation'
    assert stmt_location['Effect'] == 'Allow'
    assert stmt_location['Principal'] == {'AWS': ['*']}
    actions = (
        stmt_location['Action']
        if isinstance(stmt_location['Action'], list)
        else [stmt_location['Action']]
    )
    assert 's3:GetBucketLocation' in actions
    assert 's3:ListBucket' not in actions
    assert stmt_location['Resource'] == [f'arn:aws:s3:::{test_bucket}']

    # Statement 1: GetObject
    stmt_object = statements[1]
    assert stmt_object['Sid'] == 'PublicReadGetObject'
    assert stmt_object['Effect'] == 'Allow'
    assert stmt_object['Principal'] == {'AWS': ['*']}
    actions = (
        stmt_object['Action']
        if isinstance(stmt_object['Action'], list)
        else [stmt_object['Action']]
    )
    assert 's3:GetObject' in actions
    assert 's3:ListBucket' not in actions
    assert stmt_object['Resource'] == [f'arn:aws:s3:::{test_bucket}/*']


async def test_apply_public_read_policy_raises_on_missing_bucket(s3):
    nonexistent = f'test-bucket-{uuid.uuid4().hex[:8]}'
    with pytest.raises(ClientError):
        await apply_public_read_policy(nonexistent)
