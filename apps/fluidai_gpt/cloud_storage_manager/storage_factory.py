from storage_manager import StorageManager
import os


async def get_storage() -> StorageManager:
    # Get value from env variables
    storage = os.environ.get("STORAGE")
    if storage is not None:
        # If storage value matches one of the supported storages then return the appropriate StorageManager instance
        match storage:
            case "aws_s3":
                from aws_s3 import AWS_S3
                return AWS_S3()
            case _:
                raise ValueError(f"Unsupported vector database: {storage}")
    else:
        return None