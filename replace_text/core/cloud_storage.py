"""Cloud storage support for remote configuration and backups."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class CloudStorageError(Exception):
    """Base exception for cloud storage errors."""

    pass


class CloudStorage(ABC):
    """Abstract interface for cloud storage operations."""

    @abstractmethod
    def upload_file(self, local_path: Path, remote_path: str) -> None:
        """Upload a file to cloud storage."""
        pass

    @abstractmethod
    def download_file(self, remote_path: str, local_path: Path) -> None:
        """Download a file from cloud storage."""
        pass

    @abstractmethod
    def list_files(self, prefix: str = "") -> list[str]:
        """List files in cloud storage."""
        pass

    @abstractmethod
    def delete_file(self, remote_path: str) -> None:
        """Delete a file from cloud storage."""
        pass


class S3Storage(CloudStorage):
    """Amazon S3 storage implementation."""

    def __init__(self, bucket: str, region: str = "us-east-1"):
        self.bucket = bucket
        self.region = region
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3

            self._client = boto3.client("s3", region_name=self.region)
        return self._client

    def upload_file(self, local_path: Path, remote_path: str) -> None:
        try:
            client = self._get_client()
            client.upload_file(str(local_path), self.bucket, remote_path)
        except Exception as e:
            raise CloudStorageError(f"S3 upload failed: {e}")

    def download_file(self, remote_path: str, local_path: Path) -> None:
        try:
            client = self._get_client()
            client.download_file(self.bucket, remote_path, str(local_path))
        except Exception as e:
            raise CloudStorageError(f"S3 download failed: {e}")

    def list_files(self, prefix: str = "") -> list[str]:
        try:
            client = self._get_client()
            response = client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            if "Contents" in response:
                return [obj["Key"] for obj in response["Contents"]]
            return []
        except Exception as e:
            raise CloudStorageError(f"S3 list failed: {e}")

    def delete_file(self, remote_path: str) -> None:
        try:
            client = self._get_client()
            client.delete_object(Bucket=self.bucket, Key=remote_path)
        except Exception as e:
            raise CloudStorageError(f"S3 delete failed: {e}")


class GCSStorage(CloudStorage):
    """Google Cloud Storage implementation."""

    def __init__(self, bucket: str):
        self.bucket = bucket
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google.cloud import storage

            self._client = storage.Client()
        return self._client

    def upload_file(self, local_path: Path, remote_path: str) -> None:
        try:
            client = self._get_client()
            bucket = client.bucket(self.bucket)
            blob = bucket.blob(remote_path)
            blob.upload_from_filename(str(local_path))
        except Exception as e:
            raise CloudStorageError(f"GCS upload failed: {e}")

    def download_file(self, remote_path: str, local_path: Path) -> None:
        try:
            client = self._get_client()
            bucket = client.bucket(self.bucket)
            blob = bucket.blob(remote_path)
            blob.download_to_filename(str(local_path))
        except Exception as e:
            raise CloudStorageError(f"GCS download failed: {e}")

    def list_files(self, prefix: str = "") -> list[str]:
        try:
            client = self._get_client()
            bucket = client.bucket(self.bucket)
            blobs = bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            raise CloudStorageError(f"GCS list failed: {e}")

    def delete_file(self, remote_path: str) -> None:
        try:
            client = self._get_client()
            bucket = client.bucket(self.bucket)
            blob = bucket.blob(remote_path)
            blob.delete()
        except Exception as e:
            raise CloudStorageError(f"GCS delete failed: {e}")


def get_cloud_storage(config: dict) -> CloudStorage | None:
    storage_type = config.get("storage_type", "")
    if not storage_type:
        return None
    if storage_type == "s3":
        return S3Storage(bucket=config.get("bucket", ""), region=config.get("region", "us-east-1"))
    elif storage_type == "gcs":
        return GCSStorage(bucket=config.get("bucket", ""))
    else:
        raise CloudStorageError(f"Unknown storage type: {storage_type}")
