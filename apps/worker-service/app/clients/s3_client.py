class S3StorageClient:
    async def download_bytes(self, key: str) -> bytes:
        raise NotImplementedError("S3 download implementation is pending")


s3_storage_client = S3StorageClient()
