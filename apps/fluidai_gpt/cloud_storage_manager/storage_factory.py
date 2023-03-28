from storage_manager import StorageManager
import os


async def get_storage() -> StorageManager:
    storage = os.environ.get("STORAGE")
    if storage is not None:

        match storage:
            case "aws_s3":
                from aws_s3 import AWS_S3
                return AWS_S3()
            case _:
                raise ValueError(f"Unsupported vector database: {storage}")
    else:
        return None