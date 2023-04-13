import os
import json

import boto3
from opensearchpy import AsyncOpenSearch, AWSV4SignerAuth, RequestsHttpConnection
from requests_kerberos import HTTPKerberosAuth, OPTIONAL

from typing import Any, Dict, List, Optional
from datastore.datastore import DataStore
from models.models import (
    DocumentChunk,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding, DocumentChunkMetadata,
    Source
)
from services.date import validate_date_str

# Read environment variables for OpenSearch
OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.environ.get("OPENSEARCH_PORT", 9200))
OPENSEARCH_USERNAME = os.environ.get("OPENSEARCH_USERNAME")
OPENSEARCH_PASSWORD = os.environ.get("OPENSEARCH_PASSWORD")
OPENSEARCH_AUTH_TYPE = os.environ.get("OPENSEARCH_AUTH_TYPE", "no-auth")
OPENSEARCH_INDEX_NAME = os.environ.get("OPENSEARCH_INDEX_NAME", "open-ai-index")
OPENSEARCH_KNN_FIELD_NAME = os.environ.get("OPENSEARCH_KNN_FIELD_NAME", "embedding")
OPENSEARCH_INDEX_PRIMARIES = int(os.environ.get("OPENSEARCH_INDEX_PRIMARIES", 1))
OPENSEARCH_INDEX_REPLICAS = int(os.environ.get("OPENSEARCH_INDEX_REPLICAS", 0))
OPENSEARCH_KNN_ENGINE = os.environ.get("OPENSEARCH_KNN_ENGINE", "nmslib")
OPENSEARCH_KNN_VECTOR_DISTANCE = os.environ.get("OPENSEARCH_KNN_VECTOR_DISTANCE", "l2")
OPENSEARCH_EMBEDDING_IN_RESULT = bool(os.environ.get("OPENSEARCH_EMBEDDING_IN_RESULT", False))
OPENSEARCH_SEARCH_TYPE = os.environ.get("OPENSEARCH_SEARCH_TYPE", "vector_search")  # other values can be keyword_search(for text search), hybrid(both keyword and vector search)
CA_CERTS_FULL_PATH = os.environ.get("CA_CERTS_FULL_PATH")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")
CLOUD_SEARCH_SERVICE = os.environ.get("CLOUD_SEARCH_SERVICE", "aoss")  # use es for Amazon Elastic Search

assert OPENSEARCH_HOST is not None
assert OPENSEARCH_PORT is not None

# OpenAI Ada Embeddings Dimension
VECTOR_DIMENSION = 1536
# This is a good enough number of size.
OPENSEARCH_BULK_BATCH_SIZE = 200

index_body = {
    "settings": {
        "index.knn": "true",
        "number_of_shards": OPENSEARCH_INDEX_PRIMARIES,
        "number_of_replicas": OPENSEARCH_INDEX_REPLICAS
    },
    "mappings": {
        "properties": {
            OPENSEARCH_KNN_FIELD_NAME: {
                "type": "knn_vector",
                "dimension": VECTOR_DIMENSION,
                "method": {
                    "name": "hnsw",
                    "engine": OPENSEARCH_KNN_ENGINE
                }
            }
        }
    }
}


class OpenSearchDataStore(DataStore):

    def __init__(self):
        try:
            self.async_client = get_async_opensearch_client()
        except Exception as e:
            print(f"Error setting up OpenSearch Cluster {e}")
            raise e

    @classmethod
    async def init(cls):
        """
        Initialize the OpenSearchDataStore and does some basic validations for the datastore setup.
        :return:
        """
        data_store = cls()
        await data_store.__setup_and_validate_data_store()
        return data_store

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        doc_ids: List[str] = []
        opensearch_documents = []
        for doc_id, chunk_list in chunks.items():
            doc_ids.append(doc_id)
            print(f"Upserting document_id: {doc_id}")
            for chunk in chunk_list:
                document = {
                    "chunk_text": chunk.text,
                    "document_id": doc_id,
                    "metadata": self.__get_opensearch_metadata(chunk.metadata),
                    OPENSEARCH_KNN_FIELD_NAME: chunk.embedding,
                    "chunk_id": chunk.id
                }
                opensearch_documents.append(document)
        bulk_indexing_batches = [
            opensearch_documents[i: i + OPENSEARCH_BULK_BATCH_SIZE]
            for i in range(0, len(opensearch_documents), OPENSEARCH_BULK_BATCH_SIZE)
        ]

        batches_async_response = []
        for batch in bulk_indexing_batches:
            try:
                print(f"Indexing the batch of size: {len(batch)}")
                batches_async_response.append(self.async_client.bulk(body=build_bulk_indexing_body(batch)))
            except Exception as e:
                print(f"Error while indexing batch in OpenSearch. {e}")

        # TODO: Find a  way to remove the doc ids which got error. Problem is should we remove the docids which
        #  partially failed. Like a single chunk failed for a doc Id. This means that batching needs to be at DocId
        #  level.
        for response in batches_async_response:
            actual_response = await response
            if actual_response["errors"] is True:
                for item in actual_response["items"]:
                    index = item["index"]
                    if index.get("error") is not None:
                        print(f"Error while indexing doc id: f{index['_id']} and error is : f{index['error']}")
        return doc_ids

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and
        returns a list of query results with matching document chunks and scores.
        """
        results: List[QueryResult] = []
        # We are not using MSearch api of OpenSearch as MSearch is added via plugin(opensearch-asynchronous-search)
        # in OpenSearch. We don't want customers to have this dependency. Hence, we will do parallelization at
        # client side. MSearch: https://opensearch.org/docs/latest/api-reference/multi-search
        # TODO: Add the capability for customers to switch the parallelization using MSearch plugin.
        query_responses = []
        for query in queries:
            query_body = create_opensearch_query(query)
            print(f"Query body is : {json.dumps(query_body)}")
            query_responses.append({
                "response": self.async_client.search(body=json.dumps(query_body), index=OPENSEARCH_INDEX_NAME),
                "query": query}
            )
        for response in query_responses:
            sync_response = await response["response"]
            results.append(create_query_result(sync_response, response["query"].query))

        return results

    async def delete(self, ids: Optional[List[str]] = None, filter: Optional[DocumentMetadataFilter] = None,
                     delete_all: Optional[bool] = None) -> bool:
        """
            Removes vectors by ids, filter, or everything in the datastore.
            Multiple parameters can be used at once.
            Returns whether the operation was successful.
        """
        if delete_all:
            delete_query_body = {
                "query": {
                    "match_all": {}
                }
            }
            try:
                await self.async_client.delete_by_query(OPENSEARCH_INDEX_NAME, body=json.dumps(delete_query_body),
                                                        conflicts="proceed")
                return True
            except Exception as e:
                print(f"Error deleting all documents from index {OPENSEARCH_INDEX_NAME}. {e}")
                raise e

        # Delete by metadata_filters
        if filter:
            delete_query_body = {
                "query": {
                    "bool": {
                        "must": create_clause_for_filters(filter)
                    }
                }
            }
            try:
                print(f"Deleting documents using filter : {delete_query_body}")
                response = await self.async_client.delete_by_query(OPENSEARCH_INDEX_NAME,
                                                                   body=json.dumps(delete_query_body),
                                                                   conflicts="proceed")
                print(f"Deletion Response from filters: {response}, {response.get('failures')}")
                if not (response.get("failures") is not None and len(response['failures']) == 0):
                    raise Exception(f"Error while deleting the documents using Filer: {filter}. Response: {response}")
            except Exception as e:
                print(f"Error deleting document for filters {delete_query_body} {e}")
                raise e

        # Delete by explicit ids
        if ids:
            try:
                print(f"Deleting document for ids {ids}")
                doc_ids_clause = []
                # find all keys associated with the document ids
                for document_id in ids:
                    document_match_clause = {
                        "match": {"metadata.document_id": document_id}
                    }
                    doc_ids_clause.append(document_match_clause)
                delete_query_body = {
                    "query": {
                        "bool": {
                            "should": doc_ids_clause
                        }
                    }
                }
                response = await self.async_client.delete_by_query(OPENSEARCH_INDEX_NAME, body=delete_query_body,
                                                                   conflicts="proceed")
                print(f"Deleted document Response from delete by document_id : {response}")
            except Exception as e:
                print(f"Error deleting ids: {ids} with exception : {e}")
                raise e

        return True

    async def __setup_and_validate_data_store(self):
        await self.__check_knn_plugin_present()
        await self.__validate_index_setup()
        await self.__validate_cluster_health()

    async def __check_knn_plugin_present(self):
        response = str(await self.async_client.cat.plugins())
        if response.__contains__('opensearch-knn') is False:
            raise Exception("The OpenSearch Data store doesn't contains the K-NN plugin. Please install K-NN plugin. "
                            "Ref: https://opensearch.org/docs/latest/install-and-configure/plugins/ ")
        print("OpenSearch K-NN plugin present in OpenSearch Cluster")

    async def __validate_index_setup(self):
        if (await self.async_client.indices.exists(OPENSEARCH_INDEX_NAME)) is True:
            print(f"Index with name : {OPENSEARCH_INDEX_NAME}, already created.")
            await self.__check_if_vector_field_present()
        else:
            await self.__create_index()

    async def __check_if_vector_field_present(self):
        mappings_response = str(await self.async_client.indices.get_mapping(index=OPENSEARCH_INDEX_NAME))
        if mappings_response.__contains__("knn_vector") is False:
            raise Exception("There is no field containing knn_vector as field type. Please make sure to create a k-nn "
                            "vector field in the index mappings. Reference: "
                            "https://opensearch.org/docs/latest/search-plugins/knn/knn-index/")

    async def __create_index(self):
        print(f"Creating index with name {OPENSEARCH_INDEX_NAME}")
        response = await self.async_client.indices.create(OPENSEARCH_INDEX_NAME, body=index_body)

        if response['acknowledged'] is True:
            print("Index {} Created successfully.".format(OPENSEARCH_INDEX_NAME))
        else:
            raise Exception(f"Unable to create Index with name: {OPENSEARCH_INDEX_NAME}, response: {response}")

    async def __validate_cluster_health(self):
        cluster_health = await self.async_client.cluster.health()
        if cluster_health["status"] == "green":
            print("Cluster Status is green.")
        else:
            print(f"Cluster health is : {cluster_health['status']}, which can lead to failures during upsert, query "
                  f"and delete operations.")

    @staticmethod
    def __get_opensearch_metadata(metadata: Optional[DocumentChunkMetadata] = None) -> Dict[str, Any]:
        if metadata is None:
            return {}
        opensearch_metadata = {}
        for field, value in metadata.dict().items():
            if value is not None:
                if type(value) is Source:
                    opensearch_metadata[field] = value.value
                elif field == "created_at":
                    if validate_date_str(date_str=value):
                        opensearch_metadata[field] = value
                else:
                    opensearch_metadata[field] = value

        return opensearch_metadata


def get_async_opensearch_client() -> AsyncOpenSearch:
    """
        This function creates different auth based OpenSearch clients. Different auth types are based from
        https://github.com/opensearch-project/opensearch-py/blob/main/USER_GUIDE.md#using-different-authentication-methods
    :return: AsyncOpenSearch
    """
    hosts = [{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}]
    if OPENSEARCH_AUTH_TYPE == "no-auth":
        return AsyncOpenSearch(
            hosts=hosts,
            http_compress=True,  # enables gzip compression for request bodies
        )
    elif OPENSEARCH_AUTH_TYPE == "user-pass":
        return AsyncOpenSearch(
            hosts=hosts,
            http_auth=(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD),
            http_compress=True,  # enables gzip compression for request bodies
            use_ssl=True,
            verify_certs=True if CA_CERTS_FULL_PATH else False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            ca_certs=CA_CERTS_FULL_PATH
        )
    elif OPENSEARCH_AUTH_TYPE == "awssig4":
        return AsyncOpenSearch(
            hosts=hosts,
            http_compress=True,  # enables gzip compression for request bodies
            http_auth=AWSV4SignerAuth(boto3.Session().get_credentials(), AWS_REGION, CLOUD_SEARCH_SERVICE),
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            pool_maxsize=20
        )
    elif OPENSEARCH_AUTH_TYPE == "kerberos":
        return AsyncOpenSearch(
            hosts=hosts,
            http_compress=True,  # enables gzip compression for request bodies
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            http_auth=HTTPKerberosAuth(mutual_authentication=OPTIONAL)
        )
    else:
        raise Exception(f"The auth type: {OPENSEARCH_AUTH_TYPE} is not supported")


def create_clause_for_filters(metadata_filter: DocumentMetadataFilter) -> []:
    filters = []
    if metadata_filter.document_id:
        print(f"Filter for the document id: {metadata_filter.document_id}")
        filters.append({"match": {"metadata.document_id": metadata_filter.document_id}})

    if metadata_filter.author:
        print(f"Filter for  the author : {metadata_filter.author}")
        filters.append({"match": {"metadata.author": metadata_filter.author}})

    if metadata_filter.source:
        print(f"Filter for the source : {metadata_filter.source.value}")
        filters.append({"match": {"metadata.source": metadata_filter.source.value}})

    if metadata_filter.source_id:
        print(f"Delete for the source_id : {metadata_filter.source_id}")
        filters.append({"match": {"metadata.source_id": metadata_filter.source_id}})
    range_clause = {}
    if metadata_filter.start_date:
        print(f"Filter for the end_date : {metadata_filter.start_date}")
        range_clause["gte"] = metadata_filter.start_date
    if metadata_filter.end_date:
        print(f"Filter for the end_date : {metadata_filter.end_date}")
        range_clause["lte"] = metadata_filter.end_date

    if metadata_filter.start_date or metadata_filter.end_date:
        print(f"Adding start date and end data in query : {range_clause}")
        filters.append({"range": {"metadata.created_at": range_clause}})

    return filters


def build_bulk_indexing_body(batch) -> str:
    body = ""
    for document in batch:
        index_info = {
            "index": {
                "_index": OPENSEARCH_INDEX_NAME,
                "_id": f"doc:{document['document_id']}:chunk:{document['chunk_id']}"
            }
        }

        body = f"{body}{json.dumps(index_info)}\n{json.dumps(document)}\n"
    return body


def create_opensearch_query(query: QueryWithEmbedding) -> Dict:
    query_body = {
        "query": {
        },
        "_source": {
            "exclude": build_exclude_fields_list()
        },
        "size": query.top_k
    }
    if OPENSEARCH_SEARCH_TYPE == "vector_search":
        query_body["query"] = dict(knn={
            OPENSEARCH_KNN_FIELD_NAME: {
                "vector": query.embedding,
                "k": query.top_k
            }
        })
        if query.filter:
            query_body["post_filter"] = {
                "bool": {
                    "must": create_clause_for_filters(query.filter)
                }
            }
    elif OPENSEARCH_SEARCH_TYPE == "keyword_search":
        query_body["query"] = {
            "bool": {
                "must": {
                    "match": {
                        "chunk_text": query.query
                    }
                }
            }
        }
        if query.filter:
            query_body["query"]["bool"]["filter"] = create_clause_for_filters(query.filter)
    elif OPENSEARCH_SEARCH_TYPE == "hybrid":
        query_body["query"] = {
            "bool": {
                "should": [
                    {
                        "match": {
                            "chunk_text": query.query
                        }
                    },
                    {
                        "knn": {
                            OPENSEARCH_KNN_FIELD_NAME: {
                                "vector": query.embedding,
                                "k": query.top_k
                            }
                        }
                    }
                ]
            }
        }
        if query.filter:
            query_body['query']['bool']['filter'] = create_clause_for_filters(query.filter)
            query_body["post_filter"] = {
                "bool": {
                    "must": create_clause_for_filters(query.filter)
                }
            }
    else:
        raise Exception(
            f"The {OPENSEARCH_SEARCH_TYPE} is not supported. Please use : vector_search, keyword_search, hybrid")
    return query_body


def build_exclude_fields_list() -> List[str]:
    exclude_list = []
    if not OPENSEARCH_EMBEDDING_IN_RESULT:
        exclude_list.append(OPENSEARCH_KNN_FIELD_NAME)
    return exclude_list


def create_query_result(response: Any, query_string: str) -> QueryResult:
    hits = response["hits"]["hits"]
    results: List[DocumentChunkWithScore] = []
    for hit in hits:
        doc_source = hit["_source"]
        results.append(DocumentChunkWithScore(
            id=doc_source["document_id"],
            score=hit["_score"],
            text=doc_source["chunk_text"],
            metadata=doc_source["metadata"],
            embedding=doc_source[OPENSEARCH_KNN_FIELD_NAME] if OPENSEARCH_EMBEDDING_IN_RESULT else None
        ))
    if len(results) == 0:
        print(f"No results found for the query string: {query_string}, response: {response}")

    return QueryResult(query=query_string, results=results)
