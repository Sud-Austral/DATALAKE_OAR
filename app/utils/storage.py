import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


class MinioClient:
    """
    Cliente lazy para MinIO (S3-compatible).
    BUG FIX #4: La instancia global `storage = MinioClient()` se creaba en tiempo
    de importación, al igual que el engine de SQLAlchemy. Si MINIO_ACCESS_KEY
    no estaba disponible, boto3 fallaba silenciosamente o lanzaba un error en
    _ensure_bucket_exists(). Ahora el cliente S3 se inicializa de forma lazy.
    """

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Inicializa el cliente boto3 de forma lazy."""
        if self._client is None:
            endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
            access_key = os.getenv("MINIO_ACCESS_KEY")
            secret_key = os.getenv("MINIO_SECRET_KEY")
            secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

            if not access_key or not secret_key:
                raise RuntimeError(
                    "MINIO_ACCESS_KEY y MINIO_SECRET_KEY no están configuradas."
                )

            self._client = boto3.client(
                "s3",
                endpoint_url=f"{'https' if secure else 'http'}://{endpoint}",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version="s3v4"),
                region_name="us-east-1",
            )
            self._ensure_bucket_exists()
        return self._client

    @property
    def bucket_name(self):
        return os.getenv("MINIO_BUCKET", "oar-datalake")

    def _ensure_bucket_exists(self):
        """Verifica la existencia del bucket y lo crea si es necesario."""
        try:
            self._client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ("404", "NoSuchBucket"):
                logger.info(f"Creando bucket: {self.bucket_name}")
                self._client.create_bucket(Bucket=self.bucket_name)
            else:
                logger.error(f"Error verificando bucket: {e}")
                raise

    def upload_file(self, file_content, object_name, content_type=None):
        """Sube un objeto al bucket."""
        client = self._get_client()
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            client.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=file_content,
                **extra_args,
            )
            return f"{self.bucket_name}/{object_name}"
        except ClientError as e:
            logger.error(f"Error subiendo archivo a MinIO: {e}")
            raise

    def get_download_url(self, object_name, expires_in=3600):
        """Genera una URL firmada para descarga temporal."""
        client = self._get_client()
        try:
            return client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_name},
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            logger.error(f"Error generando URL de descarga: {e}")
            return None


# Instancia global — el cliente S3 real se crea al primer uso
storage = MinioClient()
