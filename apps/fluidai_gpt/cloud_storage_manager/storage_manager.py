import logging
import boto3
from botocore.exceptions import ClientError
import os
import io
import PyPDF2


class StorageManager:
    def __init__(self, bucket_name, aws_access_key_id=None, aws_secret_access_key=None):

        # load the aws credentials from the environment variables
        if aws_access_key_id is None and aws_secret_access_key is None:
            self.aws_access_key_id = os.getenv('ACCESS_ID')
            self.aws_secret_access_key = os.getenv('ACCESS_KEY')
        else:
            self.aws_access_key_id = aws_access_key_id
            self.aws_secret_access_key = aws_secret_access_key

        # save the variables
        self.bucket_name = bucket_name
        self.bucket = None
        self.s3_client = None
        self.s3_resource = None

        # connect t s3 bucket
        self.connect_to_s3_bucket()

    def connect_to_s3_bucket(self):
        # connect to the s3 resource
        self.s3_resource = boto3.resource('s3',
                                          aws_access_key_id=self.aws_access_key_id,
                                          aws_secret_access_key=self.aws_secret_access_key)
        # connect to the s3 client
        self.s3_client = boto3.client('s3',
                                      aws_access_key_id=self.aws_access_key_id,
                                      aws_secret_access_key=self.aws_secret_access_key)
        self.bucket = self.s3_resource.Bucket(name=self.bucket_name)

    def upload_data(self, aws_destination_path, upload_file_path=None, data_to_upload=None, upload_file_name=None):
        # check if file path is provided
        if upload_file_path:
            local_file_path = upload_file_path

            # upload a file
            self.bucket.upload_file(Filename=local_file_path, Key=aws_destination_path)

        # if data is provided to upload
        elif data_to_upload:
            # generate the file buffer
            bytes_buffer = self.generate_file_buffer(data=data_to_upload, file_name=upload_file_name)

            # upload the bytes buffer to cloud
            self.s3_client.upload_fileobj(bytes_buffer, self.bucket_name, aws_destination_path)

            # close the buffer
            bytes_buffer.close()
        else:
            # raise an error if no data is provided
            raise ValueError("Please provide file path or data to be uploaded")

        # get the pre signed url
        url = self.create_pre_signed_url(aws_destination_path)

        return url

    def download_data(self, aws_file_path, destination_path):

        # upload a file
        try:
            self.bucket.download_file(Key=aws_file_path, Filename=destination_path)
            return True
        except ClientError:
            return False

    def get_data_from_cloud(self, cloud_file_path, file_buffer):

        if not hasattr(file_buffer, 'read'):
            raise BufferError("File buffer must have a read attribute")

        # download the data from cloud into the buffer
        self.s3_client.download_fileobj(self.bucket_name, cloud_file_path, file_buffer)

        # return the file buffer
        return file_buffer

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

    def delete_file(self, aws_file_path):
        print(aws_file_path)
        # check if the file exists
        if self.check_if_file_exists(aws_file_path=aws_file_path):
            # delete a file
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=aws_file_path)

            # check if file was deleted successfully
            if self.check_if_file_exists(aws_file_path=aws_file_path):
                raise ValueError("Unable to delete file from the S3 bucket")
            else:
                return True
        else:
            raise FileNotFoundError("Unable to find document in the S3 bucket")

    def check_if_file_exists(self, aws_file_path):
        try:
            # check if the file exists now
            self.s3_client.get_object(Bucket=self.bucket_name, Key=aws_file_path)
            return True
        except ClientError:
            return False
        
    def delete_folder(self, cloud_folder_path):

        result = self.bucket.objects.filter(Prefix=cloud_folder_path).delete()

        if len(result) == 0:
            raise ValueError("The file does not exist in S3")
        return True

    @staticmethod
    def generate_file_buffer(data, file_name):
        if os.path.splitext(file_name)[-1] == '.pdf':
            # creating a pdf Reader object
            pdf_reader = PyPDF2.PdfReader(data)

            encoded_file_buffer = pdf_reader.stream.getvalue()
        else:
            # create a file buffer to load the text data into
            file_buffer = io.StringIO()

            # write the data into the buffer
            file_buffer.write(data)

            encoded_file_buffer = file_buffer.getvalue().encode()

        # generate the bytes buffer that can be used to upload to cloud
        bytes_buffer = io.BytesIO(encoded_file_buffer)

        return bytes_buffer
