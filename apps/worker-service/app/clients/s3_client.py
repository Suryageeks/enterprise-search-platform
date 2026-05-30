from __future__ import annotations

import asyncio

import boto3

from app.core.config import settings


class S3Client:
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            endpoint_url=settings.aws_endpoint_url,
        )

    async def download_bytes(self, key: str) -> bytes:
        return await asyncio.to_thread(self._download_bytes_sync, key)

    def _download_bytes_sync(self, key: str) -> bytes:
        response = self._client.get_object(
            Bucket=settings.aws_bucket_name,
            Key=key,
        )
        return response["Body"].read()


s3_client = S3Client()
