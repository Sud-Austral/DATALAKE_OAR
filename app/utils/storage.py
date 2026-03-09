import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

class MinioClient:
    """
    Cliente para interactuar con MinIO (S3-compatible).
    Maneja la persistencia física de archivos en el Datalake.
    """
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY")
        self.secret_key = os.getenv("MINIO_SECRET_KEY")
        self.bucket_name = os.getenv("MINIO_BUCKET", "oar-datalake")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        
        # Inicializar sesión de boto3
        self.s3 = boto3.client(
            's3',
            endpoint_url=f"{'https' if self.secure else 'http'}://{self.endpoint}",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        
        if self.access_key and self.secret_key:
            self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Verifica la existencia del bucket y lo crea si es necesario."""
        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.info(f"Creando bucket: {self.bucket_name}")
                self.s3.create_bucket(Bucket=self.bucket_name)
            else:
                logger.error(f"Error verificando bucket: {e}")

    def upload_file(self, file_content, object_name, content_type=None):
        """
        Sube un objeto al bucket.
        :param file_content: Contenido del archivo (bytes o file-like object)
        :param object_name: Ruta/nombre dentro del bucket
        :param content_type: Tipo MIME del archivo
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=file_content,
                **extra_args
            )
            return f"{self.bucket_name}/{object_name}"
        except ClientError as e:
            logger.error(f"Error subiendo archivo a MinIO: {e}")
            raise e

    def get_download_url(self, object_name, expires_in=3600):
        """Genera una URL firmada para descarga temporal."""
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_name},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Error generando URL de descarga: {e}")
            return None

# Instancia global para ser utilizada en los endpoints
storage = MinioClient()
