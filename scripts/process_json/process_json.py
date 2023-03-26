import uuid
import json
import argparse
import asyncio

from models.models import Document, DocumentMetadata
from datastore.datastore import DataStore
from datastore.factory import get_datastore
from services.extract_metadata import extract_metadata_from_document
from services.pii_detection import screen_text_for_pii

DOCUMENT_UPSERT_BATCH_SIZE = 50


async def process_json_dump(
    filepath: str,
    datastore: DataStore,
    custom_metadata: dict,
    screen_for_pii: bool,
    extract_metadata: bool,
):
    # load the json file as a list of dictionaries
    with open(filepath) as json_file:
        data = json.load(json_file)

    documents = []
    skipped_items = []
    # iterate over the data and create document objects
    for item in data:
        if len(documents) % 20 == 0:
            print(f"Processed {len(documents)} documents")

        try:
            # get the id, text, source, source_id, url, created_at and author from the item
            # use default values if not specified
            id = item.get("id", None)
            text = item.get("text", None)
            source = item.get("source", None)
            source_id = item.get("source_id", None)
            url = item.get("url", None)
            created_at = item.get("created_at", None)
            author = item.get("author", None)

            if not text:
                print("No document text, skipping...")
                continue

            # create a metadata object with the source, source_id, url, created_at and author
            metadata = DocumentMetadata(
                source=source,
                source_id=source_id,
                url=url,
                created_at=created_at,
                author=author,
            )
            print("metadata: ", str(metadata))

            # update metadata with custom values
            for key, value in custom_metadata.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)

            # screen for pii if requested
            if screen_for_pii:
                pii_detected = screen_text_for_pii(text)
                # if pii detected, print a warning and skip the document
                if pii_detected:
                    print("PII detected in document, skipping")
                    skipped_items.append(item)  # add the skipped item to the list
                    continue

            # extract metadata if requested
            if extract_metadata:
                # extract metadata from the document text
                extracted_metadata = extract_metadata_from_document(
                    f"Text: {text}; Metadata: {str(metadata)}"
                )
                # get a Metadata object from the extracted metadata
                metadata = DocumentMetadata(**extracted_metadata)

            # create a document object with the id or a random id, text and metadata
            document = Document(
                id=id or str(uuid.uuid4()),
                text=text,
                metadata=metadata,
            )
            documents.append(document)
        except Exception as e:
            # log the error and continue with the next item
            print(f"Error processing {item}: {e}")
            skipped_items.append(item)  # add the skipped item to the list

    # do this in batches, the upsert method already batches documents but this allows
    # us to add more descriptive logging
    for i in range(0, len(documents), DOCUMENT_UPSERT_BATCH_SIZE):
        # Get the text of the chunks in the current batch
        batch_documents = documents[i : i + DOCUMENT_UPSERT_BATCH_SIZE]
        print(f"Upserting batch of {len(batch_documents)} documents, batch {i}")
        print("documents: ", documents)
        await datastore.upsert(batch_documents)

    # print the skipped items
    print(f"Skipped {len(skipped_items)} items due to errors or PII detection")
    for item in skipped_items:
        print(item)


async def main():
    # parse the command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--filepath", required=True, help="The path to the json dump")
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
    # process the json dump
    await process_json_dump(
        filepath, datastore, custom_metadata, screen_for_pii, extract_metadata
    )


if __name__ == "__main__":
    asyncio.run(main())
