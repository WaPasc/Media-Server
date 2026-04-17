import os

import aioboto3
from dotenv import load_dotenv

load_dotenv()

S3_ENDPOINT = os.getenv('S3_ENDPOINT')
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY')
print(S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY)  # Debug print to verify values


class S3Client:
    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint_url = S3_ENDPOINT
        self.access_key = S3_ACCESS_KEY
        self.secret_key = S3_SECRET_KEY

    def get_client(self):
        return self.session.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )


s3_client = S3Client()
