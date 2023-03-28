import logging
import os
import io
import PyPDF2
from abc import abstractmethod
from apps.fluidai_gpt.models import CloudDownloadMetadata, CloudUploadMetadata, CloudDataMetadata


# Abstract Base Class for StorageManager
class StorageManager:
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def connect_to_server(self):
        pass
    
    @abstractmethod
    def upload_data(self, CloudUploadMetadata):
        pass
    
    @abstractmethod
    def download_data(self, CloudDownloadMetadata):
        pass
    
    @abstractmethod
    def get_data_from_cloud(self, CloudDataMetadata):
        pass
    
    @abstractmethod
    def delete_file(self, file_path):
        pass
    
    @abstractmethod
    def check_if_file_exists(self, file_path):
        pass
    
    @abstractmethod
    def delete_folder(self, cloud_folder_path):
        pass
    
    # Static method to generate file buffer
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
