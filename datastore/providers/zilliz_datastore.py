import os
import asyncio

from typing import Dict, List, Optional
from pymilvus import (
    Collection,
    connections,
    utility,
    FieldSchema,
    DataType,
    CollectionSchema,
)
from uuid import uuid4


from services.date import to_unix_timestamp
from datastore.datastore import DataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    Source,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
    DocumentChunkWithScore,
)

ZILLIZ_COLLECTION = os.environ.get("ZILLIZ_COLLECTION") or "c" + uuid4().hex
ZILLIZ_URI = os.environ.get("ZILLIZ_URI")
ZILLIZ_USER = os.environ.get("ZILLIZ_USER")
ZILLIZ_PASSWORD = os.environ.get("ZILLIZ_PASSWORD")
ZILLIZ_USE_SECURITY = False if ZILLIZ_PASSWORD is None else True


UPSERT_BATCH_SIZE = 100
OUTPUT_DIM = 1536


class Required:
    pass


# The fields names that we are going to be storing within Zilliz Cloud, the field declaration for schema creation, and the default value
SCHEMA = [
    (
        "pk",
        FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
        Required,
    ),
    (
        "embedding",
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=OUTPUT_DIM),
        Required,
    ),
    (
        "text",
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        Required,
    ),
    (
        "document_id",
        FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=65535),
        "",
    ),
    (
        "source_id",
        FieldSchema(name="source_id", dtype=DataType.VARCHAR, max_length=65535),
        "",
    ),
    (
        "id",
        FieldSchema(
            name="id",
            dtype=DataType.VARCHAR,
            max_length=65535,
        ),
        "",
    ),
    (
        "source",
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=65535),
        "",
    ),
    ("url", FieldSchema(name="url", dtype=DataType.VARCHAR, max_length=65535), ""),
    ("created_at", FieldSchema(name="created_at", dtype=DataType.INT64), -1),
    (
        "author",
        FieldSchema(name="author", dtype=DataType.VARCHAR, max_length=65535),
        "",
    ),
]


class ZillizDataStore(DataStore):
    def __init__(self, create_new: Optional[bool] = False):
        """Create a Zilliz DataStore.

        The Zilliz Datastore allows for storing your indexes and metadata within a Zilliz Cloud instance.

        Args:
            create_new (Optional[bool], optional): Whether to overwrite if collection already exists. Defaults to True.
        """

        # # TODO: Auto infer the fields
        # non_string_fields = [('embedding', List[float]), ('created_at', int)]
        # fields_to_index = list(DocumentChunkMetadata.__fields__.keys())
        # fields_to_index = list(DocumentChunk.__fields__.keys())

        # Check if the connection already exists
        try:
            i = [
                connections.get_connection_addr(x[0])
                for x in connections.list_connections()
            ].index({"address": ZILLIZ_URI, "user": ZILLIZ_USER})
            self.alias = connections.list_connections()[i][0]
        except ValueError:
            # Connect to the Zilliz instance using the passed in Enviroment variables
            self.alias = uuid4().hex
            connections.connect(alias=self.alias, uri=ZILLIZ_URI, user=ZILLIZ_USER, password=ZILLIZ_PASSWORD, secure=ZILLIZ_USE_SECURITY)  # type: ignore

        self._create_collection(create_new)  # type: ignore

    def _create_collection(self, create_new: bool) -> None:
        """Create a collection based on enviroment and passed in variables.

        Args:
            create_new (bool): Whether to overwrite if collection already exists.
        """

        # If the collection exists and create_new is True, drop the existing collection
        if utility.has_collection(ZILLIZ_COLLECTION, using=self.alias) and create_new:
            utility.drop_collection(ZILLIZ_COLLECTION, using=self.alias)

        # Check if the collection doesnt exist
        if utility.has_collection(ZILLIZ_COLLECTION, using=self.alias) is False:
            # If it doesnt exist use the field params from init to create a new schema
            schema = [field[1] for field in SCHEMA]
            schema = CollectionSchema(schema)
            # Use the schema to create a new collection
            self.col = Collection(
                ZILLIZ_COLLECTION,
                schema=schema,
                consistency_level="Strong",
                using=self.alias,
            )
        else:
            # If the collection exists, point to it
            self.col = Collection(ZILLIZ_COLLECTION, consistency_level="Strong", using=self.alias)  # type: ignore

        # If no index on the collection, create one
        if len(self.col.indexes) == 0:
            i_p = {"metric_type": "L2", "index_type": "AUTOINDEX", "params": {}}
            self.col.create_index("embedding", index_params=i_p)

        self.col.load()

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """Upsert chunks into the datastore.

        Args:
            chunks (Dict[str, List[DocumentChunk]]): A list of DocumentChunks to insert

        Raises:
            e: Error in upserting data.

        Returns:
            List[str]: The document_id's that were inserted.
        """
        # The doc id's to return for the upsert
        doc_ids: List[str] = []
        # List to collect all the insert data
        insert_data = [[] for _ in range(len(SCHEMA) - 1)]
        # Go through each document chunklist and grab the data
        for doc_id, chunk_list in chunks.items():
            # Append the doc_id to the list we are returning
            doc_ids.append(doc_id)
            # Examine each chunk in the chunklist
            for chunk in chunk_list:
                # Extract data from the chunk
                list_of_data = self._get_values(chunk)
                # Check if the data is valid
                if list_of_data is not None:
                    # Append each field to the insert_data
                    for x in range(len(insert_data)):
                        insert_data[x].append(list_of_data[x])
        # Slice up our insert data into batches
        batches = [
            insert_data[i : i + UPSERT_BATCH_SIZE]
            for i in range(0, len(insert_data), UPSERT_BATCH_SIZE)
        ]

        # Attempt to insert each batch into our collection
        for batch in batches:
            # Check if empty batch
            if len(batch[0]) != 0:
                try:
                    print(f"Upserting batch of size {len(batch[0])}")
                    self.col.insert(batch)
                    print(f"Upserted batch successfully")
                except Exception as e:
                    print(f"Error upserting batch: {e}")
                    raise e

        # This setting performs flushes after insert. Small insert == bad to use
        # self.col.flush()

        return doc_ids

    def _get_values(self, chunk: DocumentChunk) -> List[any] | None:  # type: ignore
        """Convert the chunk into a list of values to insert whose indexes align with fields.

        Args:
            chunk (DocumentChunk): The chunk to convert.

        Returns:
            List (any): The values to insert.
        """
        # Convert DocumentChunk and its sub models to dict
        values = chunk.dict()
        # Unpack the metadata into the same dict
        meta = values.pop("metadata")
        values.update(meta)

        # Convert date to int timestamp form
        if values["created_at"]:
            values["created_at"] = to_unix_timestamp(values["created_at"])

        # If source exists, change from Source object to the string value it holds
        if values["source"]:
            values["source"] = values["source"].value
        # List to collect data we will return
        ret = []
        # Grab data responding to each field excluding the hidden auto pk field
        for key, _, default in SCHEMA[1:]:
            # Grab the data at the key and default to our defaults set in init
            x = values.get(key) or default
            # If one of our required fields is missing, ignore the entire entry
            if x is Required:
                print("Chunk " + values["id"] + " missing " + key + " skipping")
                return None
            # Add the corresponding value if it passes the tests
            ret.append(x)
        return ret

    async def _query(
        self,
        queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """Query the QueryWithEmbedding against the ZillizDocumentSearch

        Search the embedding and its filter in the collection.

        Args:
            queries (List[QueryWithEmbedding]): The list of searches to perform.

        Returns:
            List[QueryResult]: Results for each search.
        """
        # Async to perform the query, adapted from pinecone implementation
        async def _single_query(query: QueryWithEmbedding) -> QueryResult:

            filter = None
            # Set the filter to expression that is valid for Zilliz
            if query.filter != None:
                # Either a valid filter or None will be returned
                filter = self._get_filter(query.filter)

            # Perform our search
            res = self.col.search(
                data=[query.embedding],
                anns_field="embedding",
                param={"metric_type": "L2", "params": {}},
                limit=query.top_k,
                expr=filter,
                output_fields=[
                    field[0] for field in SCHEMA[2:]
                ],  # Ignoring pk, embedding
            )
            # Results that will hold our DocumentChunkWithScores
            results = []
            # Parse every result for our search
            for hit in res[0]:  # type: ignore
                # The distance score for the search result, falls under DocumentChunkWithScore
                score = hit.score
                # Our metadata info, falls under DocumentChunkMetadata
                metadata = {}
                # Grab the values that correspond to our fields, ignore pk and embedding.
                for x in [field[0] for field in SCHEMA[2:]]:
                    metadata[x] = hit.entity.get(x)
                # If the source isnt valid, conver to None
                if metadata["source"] not in Source.__members__:
                    metadata["source"] = None
                # Text falls under the DocumentChunk
                text = metadata.pop("text")
                # Id falls under the DocumentChunk
                ids = metadata.pop("id")
                chunk = DocumentChunkWithScore(
                    id=ids,
                    score=score,
                    text=text,
                    metadata=DocumentChunkMetadata(**metadata),
                )
                results.append(chunk)

            # TODO: decide on doing queries to grab the embedding itself, slows down performance as double query occurs

            return QueryResult(query=query.query, results=results)

        results: List[QueryResult] = await asyncio.gather(
            *[_single_query(query) for query in queries]
        )
        return results

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """Delete the entities based either on the chunk_id of the vector,

        Args:
            ids (Optional[List[str]], optional): The document_ids to delete. Defaults to None.
            filter (Optional[DocumentMetadataFilter], optional): The filter to delete by. Defaults to None.
            delete_all (Optional[bool], optional): Whether to drop the collection and recreate it. Defaults to None.
        """
        # If deleting all, drop and create the new collection
        if delete_all:
            # Release the collection from memory
            self.col.release()
            # Drop the collection
            self.col.drop()
            # Recreate the new collection
            self._create_collection(True)
            return True

        # Keep track of how many we have deleted for later printing
        delete_count = 0

        # Check if empty ids
        if ids != None:
            if len(ids) != 0:
                # Add quotation marks around the string format id
                ids = ['"' + str(id) + '"' for id in ids]
                # Query for the pk's of entries that match id's
                ids = self.col.query(f"document_id in [{','.join(ids)}]")
                # Convert to list of pks
                ids = [str(entry["pk"]) for entry in ids]  # type: ignore
                # Check to see if there are valid pk's to delete
                if len(ids) != 0:
                    # Delete the entries for each pk
                    res = self.col.delete(f"pk in [{','.join(ids)}]")
                    # Increment our deleted count
                    delete_count += int(res.delete_count)  # type: ignore

        # Check if empty filter
        if filter != None:
            # Convert filter to Zilliz expression
            filter = self._get_filter(filter)  # type: ignore
            # Check if there is anything to filter
            if len(filter) != 0:  # type: ignore
                # Query for the pk's of entries that match filter
                filter = self.col.query(filter)  # type: ignore
                # Convert to list of pks
                filter = [str(entry["pk"]) for entry in filter]  # type: ignore
                # Check to see if there are valid pk's to delete
                if len(filter) != 0:  # type: ignore
                    # Delete the entries
                    res = self.col.delete(f"pk in [{','.join(filter)}]")  # type: ignore
                    # Increment our delete count
                    delete_count += int(res.delete_count)  # type: ignore

        # This setting performs flushes after delete. Small delete == bad to use
        # self.col.flush()

        return True

    def _get_filter(self, filter: DocumentMetadataFilter) -> Optional[str]:
        """Converts a DocumentMetdataFilter to the expression that Zilliz takes.

        Args:
            filter (DocumentMetadataFilter): The Filter to convert to Zilliz expression.

        Returns:
            Optional[str]: The filter if valid, otherwise None.
        """
        filters = []
        # Go through all the fields and thier values
        for field, value in filter.dict().items():
            # Check if the Value is empty
            if value is not None:
                # Convert start_date to int and add greater than or equal logic
                if field == "start_date":
                    filters.append(
                        "(created_at >= " + str(to_unix_timestamp(value)) + ")"
                    )
                # Convert end_date to int and add less than or equal logic
                elif field == "end_date":
                    filters.append(
                        "(created_at <= " + str(to_unix_timestamp(value)) + ")"
                    )
                # Convert Source to its string value and check equivalency
                elif field == "source":
                    filters.append("(" + field + ' == "' + str(value.value) + '")')
                # Check equivalency of rest of string fields
                else:
                    filters.append("(" + field + ' == "' + str(value) + '")')
        # Join all our expressions with `and``
        return " and ".join(filters)
