from storage_manager import StorageManager
import os
import boto3
from botocore.exceptions import ClientError
import logging
from apps.fluidai_gpt.models import CloudDownloadMetadata, CloudUploadMetadata, CloudDataMetadata

# For instantiating an AWS StorageManager
class AWS_S3(StorageManager):
    def __init__(self):

        # load the aws credentials from the environment variables
        self.aws_access_key_id = os.getenv('ACCESS_ID')
        self.aws_secret_access_key = os.getenv('ACCESS_KEY')
        self.bucket_name = os.getenv('BUCKET_NAME')
        if self.aws_access_key_id is None or self.aws_secret_access_key is None:
            return None

        # save the variables
        self.bucket = None
        self.s3_client = None
        self.s3_resource = None

        # connect t s3 bucket
        self.connect_to_server()

    def connect_to_server(self):
        # connect to the s3 resource
        self.s3_resource = boto3.resource('s3',
                                          aws_access_key_id=self.aws_access_key_id,
                                          aws_secret_access_key=self.aws_secret_access_key)
        # connect to the s3 client
        self.s3_client = boto3.client('s3',
                                      aws_access_key_id=self.aws_access_key_id,
                                      aws_secret_access_key=self.aws_secret_access_key)
        self.bucket = self.s3_resource.Bucket(name=self.bucket_name)

    def upload_data(self, CloudUploadMetadata):
        # check if file path is provided
        if CloudUploadMetadata.upload_file_path:
            local_file_path = CloudUploadMetadata.upload_file_path

            # upload a file
            self.bucket.upload_file(Filename=local_file_path, Key=CloudUploadMetadata.destination_path)

        # if data is provided to upload
        elif CloudUploadMetadata.data_to_upload:
            # generate the file buffer
            bytes_buffer = self.generate_file_buffer(data=CloudUploadMetadata.data_to_upload, file_name=CloudUploadMetadata.upload_file_name)

            # upload the bytes buffer to cloud
            self.s3_client.upload_fileobj(bytes_buffer, self.bucket_name, CloudUploadMetadata.destination_path)

            # close the buffer
            bytes_buffer.close()
        else:
            # raise an error if no data is provided
            raise ValueError("Please provide file path or data to be uploaded")

        # get the pre signed url
        url = self.create_pre_signed_url(CloudUploadMetadata.destination_path)

        return url

    def download_data(self, CloudDownloadMetadata):

        # upload a file
        try:
            self.bucket.download_file(Key=CloudDownloadMetadata.file_path, Filename=CloudDownloadMetadata.destination_path)
            return True
        except ClientError:
            return False

    def get_data_from_cloud(self, CloudDataMetadata):

        if not hasattr(CloudDataMetadata.file_buffer, 'read'):
            raise BufferError("File buffer must have a read attribute")

        # download the data from cloud into the buffer
        self.s3_client.download_fileobj(self.bucket_name, CloudDataMetadata.cloud_file_path, CloudDataMetadata.file_buffer)

        # return the file buffer
        return CloudDataMetadata.file_buffer

    def create_pre_signed_url(self, object_name, expiration=2592000):
        """Generate a pre signed URL of the s3 file to share an S3 object's url
        :param object_name: string
        :param expiration: Time in seconds for the presigned URL to remain valid
        :return: Presigned URL as string. If error, returns None.
        """

        try:
            # check if file exists
            if not self.check_if_file_exists(object_name):
                raise ValueError("Unable to find the object in the cloud bucket")

            response = self.s3_client.generate_presigned_url('get_object',
                                                             Params={'Bucket': self.bucket_name, 'Key': object_name},
                                                             ExpiresIn=expiration)
        except ClientError as e:
            logging.error(e)
            return None
        except ValueError:
            return None

        # The response contains the pre signed URL
        return response

    def delete_file(self, file_path):
        print(file_path)
        # check if the file exists
        if self.check_if_file_exists(file_path=file_path):
            # delete a file
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)

            # check if file was deleted successfully
            if self.check_if_file_exists(file_path=file_path):
                raise ValueError("Unable to delete file from the S3 bucket")
            else:
                return True
        else:
            raise FileNotFoundError("Unable to find document in the S3 bucket")

    def check_if_file_exists(self, file_path):
        try:
            # check if the file exists now
            self.s3_client.get_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except ClientError:
            return False
        
    def delete_folder(self, cloud_folder_path):

        result = self.bucket.objects.filter(Prefix=cloud_folder_path).delete()

        if len(result) == 0:
            raise ValueError("The file does not exist in S3")
        return True