"""
Image storage service supporting local filesystem and S3-compatible storage.
"""
import logging
import os
import hashlib
from typing import Optional, Literal
from pathlib import Path
import aiofiles

logger = logging.getLogger(__name__)


class ImageStorageService:
    """
    Service for storing and retrieving images.

    Supports:
    - Local filesystem storage
    - S3-compatible storage (MinIO, AWS S3) - future extension
    """

    def __init__(
        self,
        storage_type: Literal["local", "s3"] = "local",
        base_path: str = "backend/storage/images",
        s3_endpoint: Optional[str] = None,
        s3_access_key: Optional[str] = None,
        s3_secret_key: Optional[str] = None,
        s3_bucket: Optional[str] = None,
    ):
        """
        Initialize image storage service.

        Args:
            storage_type: Type of storage ("local" or "s3")
            base_path: Base path for local storage
            s3_endpoint: S3 endpoint URL (e.g., "http://localhost:9000" for MinIO)
            s3_access_key: S3 access key
            s3_secret_key: S3 secret key
            s3_bucket: S3 bucket name
        """
        self.storage_type = storage_type
        self.base_path = Path(base_path)

        if storage_type == "local":
            # Create base directory if it doesn't exist
            self.base_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Initialized local image storage at {self.base_path}")

        elif storage_type == "s3":
            # S3 configuration
            self.s3_endpoint = s3_endpoint
            self.s3_access_key = s3_access_key
            self.s3_secret_key = s3_secret_key
            self.s3_bucket = s3_bucket

            # Initialize S3 client (lazy loading)
            self._s3_client = None
            logger.info(f"Initialized S3 storage with bucket: {s3_bucket}")

        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")

    def _get_s3_client(self):
        """Lazy load S3 client."""
        if self._s3_client is None:
            try:
                import boto3
                self._s3_client = boto3.client(
                    's3',
                    endpoint_url=self.s3_endpoint,
                    aws_access_key_id=self.s3_access_key,
                    aws_secret_access_key=self.s3_secret_key
                )
                logger.info("S3 client initialized")
            except ImportError:
                raise ImportError("boto3 is required for S3 storage. Install with: pip install boto3")
        return self._s3_client

    def generate_image_path(
        self,
        page_id: str,
        image_index: int,
        extension: str = "png"
    ) -> str:
        """
        Generate a unique path for an image using page_id.

        This is KEY to maintaining document integrity - images are named
        with page_id so we can always find all images for a document.

        Args:
            page_id: OneNote page ID
            image_index: Index of image in the page
            extension: File extension (default: png)

        Returns:
            Relative path for the image
        """
        # Use first few chars of page_id as subfolder for better organization
        subfolder = page_id[:8] if len(page_id) >= 8 else page_id
        filename = f"{page_id}_{image_index}.{extension}"

        return f"{subfolder}/{filename}"

    def generate_image_hash(self, image_data: bytes) -> str:
        """
        Generate SHA-256 hash of image data for deduplication.

        Args:
            image_data: Image bytes

        Returns:
            Hex digest of image hash
        """
        return hashlib.sha256(image_data).hexdigest()

    async def upload(
        self,
        image_path: str,
        image_data: bytes,
        content_type: str = "image/png",
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload image to storage.

        Args:
            image_path: Relative path for the image
            image_data: Image data as bytes
            content_type: MIME type of the image
            metadata: Optional metadata to store with image

        Returns:
            Storage path/URL of uploaded image
        """
        if self.storage_type == "local":
            return await self._upload_local(image_path, image_data, metadata)
        elif self.storage_type == "s3":
            return await self._upload_s3(image_path, image_data, content_type, metadata)

    async def _upload_local(
        self,
        image_path: str,
        image_data: bytes,
        metadata: Optional[dict] = None
    ) -> str:
        """Upload image to local filesystem."""
        try:
            full_path = self.base_path / image_path

            # Create subdirectories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write image data
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(image_data)

            # Optionally write metadata as JSON
            if metadata:
                metadata_path = full_path.with_suffix('.json')
                import json
                async with aiofiles.open(metadata_path, 'w') as f:
                    await f.write(json.dumps(metadata, indent=2))

            logger.debug(f"Uploaded image to local storage: {full_path}")
            return str(image_path)

        except Exception as e:
            logger.error(f"Error uploading image to local storage: {str(e)}")
            raise

    async def _upload_s3(
        self,
        image_path: str,
        image_data: bytes,
        content_type: str,
        metadata: Optional[dict] = None
    ) -> str:
        """Upload image to S3-compatible storage."""
        try:
            s3_client = self._get_s3_client()

            # Prepare metadata for S3
            s3_metadata = metadata or {}
            s3_metadata_str = {k: str(v) for k, v in s3_metadata.items()}

            # Upload to S3
            s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=image_path,
                Body=image_data,
                ContentType=content_type,
                Metadata=s3_metadata_str
            )

            logger.debug(f"Uploaded image to S3: {image_path}")
            return f"s3://{self.s3_bucket}/{image_path}"

        except Exception as e:
            logger.error(f"Error uploading image to S3: {str(e)}")
            raise

    async def download(self, image_path: str) -> Optional[bytes]:
        """
        Download image from storage.

        Args:
            image_path: Path/URL of the image

        Returns:
            Image data as bytes, or None if not found
        """
        if self.storage_type == "local":
            return await self._download_local(image_path)
        elif self.storage_type == "s3":
            return await self._download_s3(image_path)

    async def _download_local(self, image_path: str) -> Optional[bytes]:
        """Download image from local filesystem."""
        try:
            full_path = self.base_path / image_path

            if not full_path.exists():
                logger.warning(f"Image not found: {full_path}")
                return None

            async with aiofiles.open(full_path, 'rb') as f:
                data = await f.read()

            logger.debug(f"Downloaded image from local storage: {full_path}")
            return data

        except Exception as e:
            logger.error(f"Error downloading image from local storage: {str(e)}")
            return None

    async def _download_s3(self, image_path: str) -> Optional[bytes]:
        """Download image from S3-compatible storage."""
        try:
            s3_client = self._get_s3_client()

            # Remove s3:// prefix if present
            if image_path.startswith("s3://"):
                image_path = image_path.replace(f"s3://{self.s3_bucket}/", "")

            response = s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=image_path
            )

            data = response['Body'].read()
            logger.debug(f"Downloaded image from S3: {image_path}")
            return data

        except Exception as e:
            logger.error(f"Error downloading image from S3: {str(e)}")
            return None

    async def delete(self, image_path: str) -> bool:
        """
        Delete image from storage.

        Args:
            image_path: Path/URL of the image

        Returns:
            True if deleted successfully, False otherwise
        """
        if self.storage_type == "local":
            return await self._delete_local(image_path)
        elif self.storage_type == "s3":
            return await self._delete_s3(image_path)

    async def _delete_local(self, image_path: str) -> bool:
        """Delete image from local filesystem."""
        try:
            full_path = self.base_path / image_path

            if full_path.exists():
                full_path.unlink()

                # Also delete metadata file if exists
                metadata_path = full_path.with_suffix('.json')
                if metadata_path.exists():
                    metadata_path.unlink()

                logger.debug(f"Deleted image from local storage: {full_path}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting image from local storage: {str(e)}")
            return False

    async def _delete_s3(self, image_path: str) -> bool:
        """Delete image from S3-compatible storage."""
        try:
            s3_client = self._get_s3_client()

            # Remove s3:// prefix if present
            if image_path.startswith("s3://"):
                image_path = image_path.replace(f"s3://{self.s3_bucket}/", "")

            s3_client.delete_object(
                Bucket=self.s3_bucket,
                Key=image_path
            )

            logger.debug(f"Deleted image from S3: {image_path}")
            return True

        except Exception as e:
            logger.error(f"Error deleting image from S3: {str(e)}")
            return False

    async def exists(self, image_path: str) -> bool:
        """
        Check if image exists in storage.

        Args:
            image_path: Path/URL of the image

        Returns:
            True if image exists, False otherwise
        """
        if self.storage_type == "local":
            full_path = self.base_path / image_path
            return full_path.exists()

        elif self.storage_type == "s3":
            try:
                s3_client = self._get_s3_client()

                # Remove s3:// prefix if present
                if image_path.startswith("s3://"):
                    image_path = image_path.replace(f"s3://{self.s3_bucket}/", "")

                s3_client.head_object(
                    Bucket=self.s3_bucket,
                    Key=image_path
                )
                return True

            except:
                return False

    def get_public_url(self, image_path: str) -> str:
        """
        Get public URL for an image (useful for S3 with public access).

        Args:
            image_path: Path of the image

        Returns:
            Public URL or local path
        """
        if self.storage_type == "local":
            return f"/storage/images/{image_path}"

        elif self.storage_type == "s3":
            # Remove s3:// prefix if present
            if image_path.startswith("s3://"):
                image_path = image_path.replace(f"s3://{self.s3_bucket}/", "")

            return f"{self.s3_endpoint}/{self.s3_bucket}/{image_path}"

    async def delete_by_page_id(self, page_id: str) -> int:
        """
        Delete all images for a specific page_id.

        This is important for maintaining consistency when deleting documents.

        Args:
            page_id: OneNote page ID

        Returns:
            Number of images deleted
        """
        deleted_count = 0

        if self.storage_type == "local":
            # Find all images for this page_id
            subfolder = page_id[:8] if len(page_id) >= 8 else page_id
            folder_path = self.base_path / subfolder

            if folder_path.exists():
                # Find all files matching page_id pattern
                pattern = f"{page_id}_*.png"
                for image_file in folder_path.glob(pattern):
                    try:
                        image_file.unlink()
                        deleted_count += 1

                        # Also delete metadata file
                        metadata_file = image_file.with_suffix('.json')
                        if metadata_file.exists():
                            metadata_file.unlink()

                    except Exception as e:
                        logger.error(f"Error deleting {image_file}: {str(e)}")

            logger.info(f"Deleted {deleted_count} images for page_id {page_id}")

        elif self.storage_type == "s3":
            # List and delete all objects with page_id prefix
            s3_client = self._get_s3_client()
            subfolder = page_id[:8] if len(page_id) >= 8 else page_id
            prefix = f"{subfolder}/{page_id}_"

            try:
                response = s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix=prefix
                )

                if 'Contents' in response:
                    for obj in response['Contents']:
                        s3_client.delete_object(
                            Bucket=self.s3_bucket,
                            Key=obj['Key']
                        )
                        deleted_count += 1

                logger.info(f"Deleted {deleted_count} images for page_id {page_id} from S3")

            except Exception as e:
                logger.error(f"Error deleting images for page_id {page_id}: {str(e)}")

        return deleted_count
