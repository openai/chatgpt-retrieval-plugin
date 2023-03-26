import uuid
import zipfile
import os
import json
import argparse
import asyncio

from models.models import Document, DocumentMetadata, Source
from datastore.datastore import DataStore
from datastore.factory import get_datastore
from services.extract_metadata import extract_metadata_from_document
from services.file import extract_text_from_filepath
from services.pii_detection import screen_text_for_pii

DOCUMENT_UPSERT_BATCH_SIZE = 50


async def process_file_dump(
    filepath: str,
    datastore: DataStore,
    custom_metadata: dict,
    screen_for_pii: bool,
    extract_metadata: bool,
):
    # create a ZipFile object and extract all the files into a directory named 'dump'
    with zipfile.ZipFile(filepath) as zip_file:
        zip_file.extractall("dump")

    documents = []
    skipped_files = []
    # use os.walk to traverse the dump directory and its subdirectories
    for root, dirs, files in os.walk("dump"):
        for filename in files:
            if len(documents) % 20 == 0:
                print(f"Processed {len(documents)} documents")

            filepath = os.path.join(root, filename)

            try:
                extracted_text = extract_text_from_filepath(filepath)
                print(f"extracted_text from {filepath}")

                # create a metadata object with the source and source_id fields
                metadata = DocumentMetadata(
                    source=Source.file,
                    source_id=filename,
                )

                # update metadata with custom values
                for key, value in custom_metadata.items():
                    if hasattr(metadata, key):
                        setattr(metadata, key, value)

                # screen for pii if requested
                if screen_for_pii:
                    pii_detected = screen_text_for_pii(extracted_text)
                    # if pii detected, print a warning and skip the document
                    if pii_detected:
                        print("PII detected in document, skipping")
                        skipped_files.append(
                            filepath
                        )  # add the skipped file to the list
                        continue

                # extract metadata if requested
                if extract_metadata:
                    # extract metadata from the document text
                    extracted_metadata = extract_metadata_from_document(
                        f"Text: {extracted_text}; Metadata: {str(metadata)}"
                    )
                    # get a Metadata object from the extracted metadata
                    metadata = DocumentMetadata(**extracted_metadata)

                # create a document object with a random id, text and metadata
                document = Document(
                    id=str(uuid.uuid4()),
                    text=extracted_text,
                    metadata=metadata,
                )
                documents.append(document)
            except Exception as e:
                # log the error and continue with the next file
                print(f"Error processing {filepath}: {e}")
                skipped_files.append(filepath)  # add the skipped file to the list

    # do this in batches, the upsert method already batches documents but this allows
    # us to add more descriptive logging
    for i in range(0, len(documents), DOCUMENT_UPSERT_BATCH_SIZE):
        # Get the text of the chunks in the current batch
        batch_documents = [doc for doc in documents[i : i + DOCUMENT_UPSERT_BATCH_SIZE]]
        print(f"Upserting batch of {len(batch_documents)} documents, batch {i}")
        print("documents: ", documents)
        await datastore.upsert(batch_documents)

    # delete all files in the dump directory
    for root, dirs, files in os.walk("dump", topdown=False):
        for filename in files:
            filepath = os.path.join(root, filename)
            os.remove(filepath)
        for dirname in dirs:
            dirpath = os.path.join(root, dirname)
            os.rmdir(dirpath)

    # delete the dump directory
    os.rmdir("dump")

    # print the skipped files
    print(f"Skipped {len(skipped_files)} files due to errors or PII detection")
    for file in skipped_files:
        print(file)


async def main():
    # parse the command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--filepath", required=True, help="The path to the file dump")
    parser.add_argument(
        "--custom_metadata",
        default="{}",
        help="A JSON string of key-value pairs to update the metadata of the documents",
    )
    parser.add_argument(
        "--screen_for_pii",
        default=False,
        type=bool,
        help="A boolean flag to indicate whether to try the PII detection function (using a language model)",
    )
    parser.add_argument(
        "--extract_metadata",
        default=False,
        type=bool,
        help="A boolean flag to indicate whether to try to extract metadata from the document (using a language model)",
    )
    args = parser.parse_args()

    # get the arguments
    filepath = args.filepath
    custom_metadata = json.loads(args.custom_metadata)
    screen_for_pii = args.screen_for_pii
    extract_metadata = args.extract_metadata

    # initialize the db instance once as a global variable
    datastore = await get_datastore()
    # process the file dump
    await process_file_dump(
        filepath, datastore, custom_metadata, screen_for_pii, extract_metadata
    )


if __name__ == "__main__":
    asyncio.run(main())
