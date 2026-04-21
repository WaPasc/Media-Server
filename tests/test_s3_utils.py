import json
import uuid

import pytest

from app.core.s3 import s3_client
from app.utils.s3_utils import apply_public_read_policy, ensure_bucket_exists

pytestmark = pytest.mark.asyncio


async def test_ensure_bucket_exists_creates_bucket():
    test_bucket = f'test-bucket-{uuid.uuid4().hex[:8]}'

    async with s3_client.get_client() as s3:
        try:
            await ensure_bucket_exists(test_bucket)

            response = await s3.head_bucket(Bucket=test_bucket)
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        finally:
            await s3.delete_bucket(Bucket=test_bucket)


async def test_apply_public_read_policy_sets_correct_statements():
    test_bucket = f'test-bucket-{uuid.uuid4().hex[:8]}'

    async with s3_client.get_client() as s3:
        try:
            # await s3.create_bucket(Bucket=test_bucket)
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
        finally:
            await s3.delete_bucket_policy(Bucket=test_bucket)
            await s3.delete_bucket(Bucket=test_bucket)


async def test_ensure_bucket_exists_is_idempotent():
    test_bucket = f'test-bucket-{uuid.uuid4().hex[:8]}'

    async with s3_client.get_client() as s3:
        try:
            await ensure_bucket_exists(test_bucket)
            await ensure_bucket_exists(test_bucket)  # should not raise

            response = await s3.head_bucket(Bucket=test_bucket)
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        finally:
            await s3.delete_bucket(Bucket=test_bucket)
