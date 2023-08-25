## Process a JSON File

This script is a utility to process a file dump of documents in a JSON format and store them in the vector database with some metadata. It can also optionally screen the documents for personally identifiable information (PII) using a language model, and skip them if detected. Additionally, the script can extract metadata from the document using a language model. You can customize the PII detection function in [`services/pii_detection`](../../services/pii_detection.py) and the metadata extraction function in [`services/extract_metadata`](../../services/extract_metadata.py) for your use case.

## Usage

To run this script from the terminal, navigate to this folder and use the following command:

```
python process_json.py --filepath path/to/file_dump.json --custom_metadata '{"source": "file"}' --screen_for_pii True --extract_metadata True
```

where:

- `path/to/file_dump.json` is the name or path to the file dump to be processed. The format of this JSON file should be a list of JSON objects, where each object represents a document. The JSON object should have a subset of the following fields: `id`, `text`, `source`, `source_id`, `url`, `created_at`, and `author`. The `text` field is required, while the rest are optional and will be used to populate the metadata of the document. If the `id` field is not specified, a random UUID will be generated for the document.
- `--custom_metadata` is an optional JSON string of key-value pairs to update the metadata of the documents. For example, `{"source": "file"}` will add a `source` field with the value `file` to the metadata of each document. The default value is an empty JSON object (`{}`).
- `--screen_for_pii` is an optional boolean flag to indicate whether to use the PII detection function or not. If set to `True`, the script will use the `screen_text_for_pii` function from the [`services/pii_detection`](../../services/pii_detection.py) module to check if the document text contains any PII using a language model. If PII is detected, the script will print a warning and skip the document. The default value is `False`.
- `--extract_metadata` is an optional boolean flag to indicate whether to try to extract metadata from the document using a language model. If set to `True`, the script will use the `extract_metadata_from_document` function from the [`services/extract_metadata`](../../services/extract_metadata.py) module to extract metadata from the document text and update the metadata object accordingly. The default value is`False`.

The script will load the JSON file as a list of dictionaries, iterate over the data, create document objects, and batch upsert them into the database. It will also print some progress messages and error messages if any, as well as the number and content of the skipped items due to errors or PII detection.

You can use `python process_json.py -h` to get a summary of the options and their descriptions.

Test the script with the example file, [example.json](example.json).
