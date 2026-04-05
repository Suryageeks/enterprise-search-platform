import asyncio

import boto3

from app.core.config import Settings


class S3Client:
    async def __init__(self) -> None:
        self._client = boto3.client(
            's3',
            region_name=Settings.aws_region,
            aws_access_key_id=Settings.aws_access_key_id,
            aws_secret_access_key=Settings.aws_secret_access_key,
            endpoint_url=Settings.aws_endpoint_url
        )
        
    async def download_bytes(self, key: str) -> bytes:
        return await asyncio.to_thread(self._download_file_bytes_sync, key)
    
    def _download_file_bytes_sync(self, key: str) -> bytes:
        response = self._client.get_object(
            Bucket=Settings.aws_bucket_name,
            Key=key
        )
        return response['Body'].read()



s3_client = S3Client()
