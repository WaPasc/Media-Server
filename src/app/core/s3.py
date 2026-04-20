import os

import aioboto3
from dotenv import load_dotenv

load_dotenv()

S3_ENDPOINT = os.getenv('S3_ENDPOINT')
S3_ACCESS_KEY = os.getenv('MINIO_ROOT_USER')
S3_SECRET_KEY = os.getenv('MINIO_ROOT_PASSWORD')
S3_IMAGES_BUCKET = os.getenv('S3_IMAGES_BUCKET')
S3_PUBLIC_BASE_URL = os.getenv('S3_PUBLIC_BASE_URL', S3_ENDPOINT)


class S3Client:
    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint_url = S3_ENDPOINT
        self.access_key = S3_ACCESS_KEY
        self.secret_key = S3_SECRET_KEY
        self.images_bucket = S3_IMAGES_BUCKET
        self.public_base_url = S3_PUBLIC_BASE_URL

    def get_client(self):
        return self.session.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    def build_public_url(self, key: str, bucket: str | None = None) -> str:
        target_bucket = bucket or self.images_bucket
        base = (self.public_base_url or '').rstrip('/')
        return f'{base}/{target_bucket}/{key.lstrip("/")}'


s3_client = S3Client()
