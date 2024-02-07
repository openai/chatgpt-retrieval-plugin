import json
import os
import asyncio

from loguru import logger
from typing import Dict, List, Optional
from pymilvus import (
    Collection,
    connections,
    utility,
    FieldSchema,
    DataType,
    CollectionSchema,
    MilvusException,
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

MILVUS_COLLECTION = os.environ.get("MILVUS_COLLECTION") or "c" + uuid4().hex
MILVUS_HOST = os.environ.get("MILVUS_HOST") or "localhost"
MILVUS_PORT = os.environ.get("MILVUS_PORT") or 19530
MILVUS_USER = os.environ.get("MILVUS_USER")
MILVUS_PASSWORD = os.environ.get("MILVUS_PASSWORD")
MILVUS_USE_SECURITY = False if MILVUS_PASSWORD is None else True

MILVUS_INDEX_PARAMS = os.environ.get("MILVUS_INDEX_PARAMS")
MILVUS_SEARCH_PARAMS = os.environ.get("MILVUS_SEARCH_PARAMS")
MILVUS_CONSISTENCY_LEVEL = os.environ.get("MILVUS_CONSISTENCY_LEVEL")

UPSERT_BATCH_SIZE = 100
OUTPUT_DIM = int(os.environ.get("EMBEDDING_DIMENSION", 256))
EMBEDDING_FIELD = "embedding"


class Required:
    pass


# The fields names that we are going to be storing within Milvus, the field declaration for schema creation, and the default value
SCHEMA_V1 = [
    (
        "pk",
        FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
        Required,
    ),
    (
        EMBEDDING_FIELD,
        FieldSchema(name=EMBEDDING_FIELD, dtype=DataType.FLOAT_VECTOR, dim=OUTPUT_DIM),
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

# V2 schema, remomve the "pk" field
SCHEMA_V2 = SCHEMA_V1[1:]
SCHEMA_V2[4][1].is_primary = True


class MilvusDataStore(DataStore):
    def __init__(
        self,
        create_new: Optional[bool] = False,
        consistency_level: str = "Bounded",
    ):
        """Create a Milvus DataStore.

        The Milvus Datastore allows for storing your indexes and metadata within a Milvus instance.

        Args:
            create_new (Optional[bool], optional): Whether to overwrite if collection already exists. Defaults to True.
            consistency_level(str, optional): Specify the collection consistency level.
                                                Defaults to "Bounded" for search performance.
                                                Set to "Strong" in test cases for result validation.
        """
        # Overwrite the default consistency level by MILVUS_CONSISTENCY_LEVEL
        self._consistency_level = MILVUS_CONSISTENCY_LEVEL or consistency_level
        self._create_connection()

        self._create_collection(MILVUS_COLLECTION, create_new)  # type: ignore
        self._create_index()

    def _get_schema(self):
        return SCHEMA_V1 if self._schema_ver == "V1" else SCHEMA_V2

    def _create_connection(self):
        try:
            self.alias = ""
            # Check if the connection already exists
            for x in connections.list_connections():
                addr = connections.get_connection_addr(x[0])
                if (
                    x[1]
                    and ("address" in addr)
                    and (addr["address"] == "{}:{}".format(MILVUS_HOST, MILVUS_PORT))
                ):
                    self.alias = x[0]
                    logger.info(
                        "Reuse connection to Milvus server '{}:{}' with alias '{:s}'".format(
                            MILVUS_HOST, MILVUS_PORT, self.alias
                        )
                    )
                    break

            # Connect to the Milvus instance using the passed in Environment variables
            if len(self.alias) == 0:
                self.alias = uuid4().hex
                connections.connect(
                    alias=self.alias,
                    host=MILVUS_HOST,
                    port=MILVUS_PORT,
                    user=MILVUS_USER,  # type: ignore
                    password=MILVUS_PASSWORD,  # type: ignore
                    secure=MILVUS_USE_SECURITY,
                )
                logger.info(
                    "Create connection to Milvus server '{}:{}' with alias '{:s}'".format(
                        MILVUS_HOST, MILVUS_PORT, self.alias
                    )
                )
        except Exception as e:
            logger.error(
                "Failed to create connection to Milvus server '{}:{}', error: {}".format(
                    MILVUS_HOST, MILVUS_PORT, e
                )
            )

    def _create_collection(self, collection_name, create_new: bool) -> None:
        """Create a collection based on environment and passed in variables.

        Args:
            create_new (bool): Whether to overwrite if collection already exists.
        """
        try:
            self._schema_ver = "V1"
            # If the collection exists and create_new is True, drop the existing collection
            if utility.has_collection(collection_name, using=self.alias) and create_new:
                utility.drop_collection(collection_name, using=self.alias)

            # Check if the collection doesnt exist
            if utility.has_collection(collection_name, using=self.alias) is False:
                # If it doesnt exist use the field params from init to create a new schem
                schema = [field[1] for field in SCHEMA_V2]
                schema = CollectionSchema(schema)
                # Use the schema to create a new collection
                self.col = Collection(
                    collection_name,
                    schema=schema,
                    using=self.alias,
                    consistency_level=self._consistency_level,
                )
                self._schema_ver = "V2"
                logger.info(
                    "Create Milvus collection '{}' with schema {} and consistency level {}".format(
                        collection_name, self._schema_ver, self._consistency_level
                    )
                )
            else:
                # If the collection exists, point to it
                self.col = Collection(collection_name, using=self.alias)  # type: ignore
                # Which sechma is used
                for field in self.col.schema.fields:
                    if field.name == "id" and field.is_primary:
                        self._schema_ver = "V2"
                        break
                logger.info(
                    "Milvus collection '{}' already exists with schema {}".format(
                        collection_name, self._schema_ver
                    )
                )
        except Exception as e:
            logger.error(
                "Failed to create collection '{}', error: {}".format(collection_name, e)
            )

    def _create_index(self):
        # TODO: verify index/search params passed by os.environ
        self.index_params = MILVUS_INDEX_PARAMS or None
        self.search_params = MILVUS_SEARCH_PARAMS or None
        try:
            # If no index on the collection, create one
            if len(self.col.indexes) == 0:
                if self.index_params is not None:
                    # Convert the string format to JSON format parameters passed by MILVUS_INDEX_PARAMS
                    self.index_params = json.loads(self.index_params)
                    logger.info("Create Milvus index: {}".format(self.index_params))
                    # Create an index on the 'embedding' field with the index params found in init
                    self.col.create_index(
                        EMBEDDING_FIELD, index_params=self.index_params
                    )
                else:
                    # If no index param supplied, to first create an HNSW index for Milvus
                    try:
                        i_p = {
                            "metric_type": "IP",
                            "index_type": "HNSW",
                            "params": {"M": 8, "efConstruction": 64},
                        }
                        logger.info(
                            "Attempting creation of Milvus '{}' index".format(
                                i_p["index_type"]
                            )
                        )
                        self.col.create_index(EMBEDDING_FIELD, index_params=i_p)
                        self.index_params = i_p
                        logger.info(
                            "Creation of Milvus '{}' index successful".format(
                                i_p["index_type"]
                            )
                        )
                    # If create fails, most likely due to being Zilliz Cloud instance, try to create an AutoIndex
                    except MilvusException:
                        logger.info("Attempting creation of Milvus default index")
                        i_p = {
                            "metric_type": "IP",
                            "index_type": "AUTOINDEX",
                            "params": {},
                        }
                        self.col.create_index(EMBEDDING_FIELD, index_params=i_p)
                        self.index_params = i_p
                        logger.info("Creation of Milvus default index successful")
            # If an index already exists, grab its params
            else:
                # How about if the first index is not vector index?
                for index in self.col.indexes:
                    idx = index.to_dict()
                    if idx["field"] == EMBEDDING_FIELD:
                        logger.info("Index already exists: {}".format(idx))
                        self.index_params = idx["index_param"]
                        break

            self.col.load()

            if self.search_params is not None:
                # Convert the string format to JSON format parameters passed by MILVUS_SEARCH_PARAMS
                self.search_params = json.loads(self.search_params)
            else:
                # The default search params
                metric_type = "IP"
                if "metric_type" in self.index_params:
                    metric_type = self.index_params["metric_type"]
                default_search_params = {
                    "IVF_FLAT": {"metric_type": metric_type, "params": {"nprobe": 10}},
                    "IVF_SQ8": {"metric_type": metric_type, "params": {"nprobe": 10}},
                    "IVF_PQ": {"metric_type": metric_type, "params": {"nprobe": 10}},
                    "HNSW": {"metric_type": metric_type, "params": {"ef": 10}},
                    "RHNSW_FLAT": {"metric_type": metric_type, "params": {"ef": 10}},
                    "RHNSW_SQ": {"metric_type": metric_type, "params": {"ef": 10}},
                    "RHNSW_PQ": {"metric_type": metric_type, "params": {"ef": 10}},
                    "IVF_HNSW": {
                        "metric_type": metric_type,
                        "params": {"nprobe": 10, "ef": 10},
                    },
                    "ANNOY": {"metric_type": metric_type, "params": {"search_k": 10}},
                    "AUTOINDEX": {"metric_type": metric_type, "params": {}},
                }
                # Set the search params
                self.search_params = default_search_params[
                    self.index_params["index_type"]
                ]
            logger.info("Milvus search parameters: {}".format(self.search_params))
        except Exception as e:
            logger.error("Failed to create index, error: {}".format(e))

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """Upsert chunks into the datastore.

        Args:
            chunks (Dict[str, List[DocumentChunk]]): A list of DocumentChunks to insert

        Raises:
            e: Error in upserting data.

        Returns:
            List[str]: The document_id's that were inserted.
        """
        try:
            # The doc id's to return for the upsert
            doc_ids: List[str] = []
            # List to collect all the insert data, skip the "pk" for schema V1
            offset = 1 if self._schema_ver == "V1" else 0
            insert_data = [[] for _ in range(len(self._get_schema()) - offset)]

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
            # batch data can work with both V1 and V2 schema
            for batch in batches:
                if len(batch[0]) != 0:
                    try:
                        logger.info(f"Upserting batch of size {len(batch[0])}")
                        self.col.insert(batch)
                        logger.info(f"Upserted batch successfully")
                    except Exception as e:
                        logger.error(f"Failed to insert batch records, error: {e}")
                        raise e

            # This setting perfoms flushes after insert. Small insert == bad to use
            # self.col.flush()
            return doc_ids
        except Exception as e:
            logger.error("Failed to insert records, error: {}".format(e))
            return []

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
        # Grab data responding to each field, excluding the hidden auto pk field for schema V1
        offset = 1 if self._schema_ver == "V1" else 0
        for key, _, default in self._get_schema()[offset:]:
            # Grab the data at the key and default to our defaults set in init
            x = values.get(key) or default
            # If one of our required fields is missing, ignore the entire entry
            if x is Required:
                logger.info("Chunk " + values["id"] + " missing " + key + " skipping")
                return None
            # Add the corresponding value if it passes the tests
            ret.append(x)
        return ret

    async def _query(
        self,
        queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """Query the QueryWithEmbedding against the MilvusDocumentSearch

        Search the embedding and its filter in the collection.

        Args:
            queries (List[QueryWithEmbedding]): The list of searches to perform.

        Returns:
            List[QueryResult]: Results for each search.
        """

        # Async to perform the query, adapted from pinecone implementation
        async def _single_query(query: QueryWithEmbedding) -> QueryResult:
            try:
                filter = None
                # Set the filter to expression that is valid for Milvus
                if query.filter is not None:
                    # Either a valid filter or None will be returned
                    filter = self._get_filter(query.filter)

                # Perform our search
                return_from = 2 if self._schema_ver == "V1" else 1
                res = self.col.search(
                    data=[query.embedding],
                    anns_field=EMBEDDING_FIELD,
                    param=self.search_params,
                    limit=query.top_k,
                    expr=filter,
                    output_fields=[
                        field[0] for field in self._get_schema()[return_from:]
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
                    for x in [field[0] for field in self._get_schema()[return_from:]]:
                        metadata[x] = hit.entity.get(x)
                    # If the source isn't valid, convert to None
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
            except Exception as e:
                logger.error("Failed to query, error: {}".format(e))
                return QueryResult(query=query.query, results=[])

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
            coll_name = self.col.name
            logger.info(
                "Delete the entire collection {} and create new one".format(coll_name)
            )
            # Release the collection from memory
            self.col.release()
            # Drop the collection
            self.col.drop()
            # Recreate the new collection
            self._create_collection(coll_name, True)
            self._create_index()
            return True

        # Keep track of how many we have deleted for later printing
        delete_count = 0
        batch_size = 100
        pk_name = "pk" if self._schema_ver == "V1" else "id"
        try:
            # According to the api design, the ids is a list of document_id,
            # document_id is not primary key, use query+delete to workaround,
            # in future version we can delete by expression
            if (ids is not None) and len(ids) > 0:
                # Add quotation marks around the string format id
                ids = ['"' + str(id) + '"' for id in ids]
                # Query for the pk's of entries that match id's
                ids = self.col.query(f"document_id in [{','.join(ids)}]")
                # Convert to list of pks
                pks = [str(entry[pk_name]) for entry in ids]  # type: ignore
                # for schema V2, the "id" is varchar, rewrite the expression
                if self._schema_ver != "V1":
                    pks = ['"' + pk + '"' for pk in pks]

                # Delete by ids batch by batch(avoid too long expression)
                logger.info(
                    "Apply {:d} deletions to schema {:s}".format(
                        len(pks), self._schema_ver
                    )
                )
                while len(pks) > 0:
                    batch_pks = pks[:batch_size]
                    pks = pks[batch_size:]
                    # Delete the entries batch by batch
                    res = self.col.delete(f"{pk_name} in [{','.join(batch_pks)}]")
                    # Increment our deleted count
                    delete_count += int(res.delete_count)  # type: ignore
        except Exception as e:
            logger.error("Failed to delete by ids, error: {}".format(e))

        try:
            # Check if empty filter
            if filter is not None:
                # Convert filter to milvus expression
                filter = self._get_filter(filter)  # type: ignore
                # Check if there is anything to filter
                if len(filter) != 0:  # type: ignore
                    # Query for the pk's of entries that match filter
                    res = self.col.query(filter)  # type: ignore
                    # Convert to list of pks
                    pks = [str(entry[pk_name]) for entry in res]  # type: ignore
                    # for schema V2, the "id" is varchar, rewrite the expression
                    if self._schema_ver != "V1":
                        pks = ['"' + pk + '"' for pk in pks]
                    # Check to see if there are valid pk's to delete, delete batch by batch(avoid too long expression)
                    while len(pks) > 0:  # type: ignore
                        batch_pks = pks[:batch_size]
                        pks = pks[batch_size:]
                        # Delete the entries batch by batch
                        res = self.col.delete(f"{pk_name} in [{','.join(batch_pks)}]")  # type: ignore
                        # Increment our delete count
                        delete_count += int(res.delete_count)  # type: ignore
        except Exception as e:
            logger.error("Failed to delete by filter, error: {}".format(e))

        logger.info("{:d} records deleted".format(delete_count))

        # This setting performs flushes after delete. Small delete == bad to use
        # self.col.flush()

        return True

    def _get_filter(self, filter: DocumentMetadataFilter) -> Optional[str]:
        """Converts a DocumentMetdataFilter to the expression that Milvus takes.

        Args:
            filter (DocumentMetadataFilter): The Filter to convert to Milvus expression.

        Returns:
            Optional[str]: The filter if valid, otherwise None.
        """
        filters = []
        # Go through all the fields and their values
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
