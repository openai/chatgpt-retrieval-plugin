import asyncio
import datetime
import json
import os
from typing import Dict, List, Optional

from alibabacloud_ha3engine import models, client
from alibabacloud_tea_util import models as util_models
from loguru import logger

from datastore.datastore import DataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
    DocumentChunkWithScore)

OS_CONFIG_PARA_NAME_ENDPOINT = "endpoint"
OS_CONFIG_PARA_NAME_INSTANCE_ID = "instance_id"
OS_CONFIG_PARA_NAME_PROTOCOL = "protocol"
OS_CONFIG_PARA_NAME_TABLE_NAME = "table_name"
OS_CONFIG_PARA_NAME_ALIYUN_USER_NAME = "access_user_name"
OS_CONFIG_PARA_NAME_ALIYUN_PASSWORD = "access_pass_word"
OS_CONFIG_PARA_NAME_EMBEDDING_INDEX_NAME = "embedding_index_name"

# Allow overriding field names for Alibaba Cloud OpenSearch
OS_FIELDS_ID = os.environ.get("OS_FIELDS_ID", "id")
OS_FIELDS_TEXT = os.environ.get("OS_FIELDS_TEXT", "text")
OS_FIELDS_EMBEDDING = os.environ.get("OS_FIELDS_EMBEDDING", "embedding")
OS_FIELDS_DOCUMENT_ID = os.environ.get("OS_FIELDS_DOCUMENT_ID", "document_id")
OS_FIELDS_SOURCE = os.environ.get("OS_FIELDS_SOURCE", "source")
OS_FIELDS_SOURCE_ID = os.environ.get("OS_FIELDS_SOURCE_ID", "source_id")
OS_FIELDS_URL = os.environ.get("OS_FIELDS_URL", "url")
OS_FIELDS_CREATED_AT = os.environ.get("OS_FIELDS_CREATED_AT", "created_at")
OS_FIELDS_AUTHOR = os.environ.get("OS_FIELDS_AUTHOR", "author")

OS_CONFIG = {
    OS_CONFIG_PARA_NAME_ENDPOINT: os.environ.get("OS_ENDPOINT", "your alibaba cloud opensearch instance endpoint"),
    OS_CONFIG_PARA_NAME_INSTANCE_ID: os.environ.get("OS_INSTANCE_ID", "your alibaba cloud opensearch instance id"),
    OS_CONFIG_PARA_NAME_PROTOCOL: os.environ.get("OS_PROTOCOL", "http"),
    OS_CONFIG_PARA_NAME_TABLE_NAME: os.environ.get("OS_TABLE_NAME", "your alibaba cloud opensearch instance table name"),
    OS_CONFIG_PARA_NAME_ALIYUN_USER_NAME: os.environ.get("OS_ACCESS_USER_NAME",
                                                         "your alibaba cloud opensearch instance user name"),
    OS_CONFIG_PARA_NAME_ALIYUN_PASSWORD: os.environ.get("OS_ACCESS_PASS_WORD",
                                                        "your alibaba cloud opensearch instance password"),
    OS_CONFIG_PARA_NAME_EMBEDDING_INDEX_NAME: os.environ.get("OS_EMBEDDING_INDEX_NAME",
                                                             "your alibaba cloud opensearch instance embedding index name")
}

OUTPUT_DIM = 1536

class AlibabaCloudOpenSearchDataStore(DataStore):
    def __init__(self):
        self.osConfig = models.Config(
            endpoint=OS_CONFIG[OS_CONFIG_PARA_NAME_ENDPOINT],
            instance_id=OS_CONFIG[OS_CONFIG_PARA_NAME_INSTANCE_ID],
            protocol=OS_CONFIG[OS_CONFIG_PARA_NAME_PROTOCOL],
            access_user_name=OS_CONFIG[OS_CONFIG_PARA_NAME_ALIYUN_USER_NAME],
            access_pass_word=OS_CONFIG[OS_CONFIG_PARA_NAME_ALIYUN_PASSWORD]
        )

        self.runtime = util_models.RuntimeOptions(
            connect_timeout=5000,
            read_timeout=10000,
            autoretry=False,
            ignore_ssl=False,
            max_idle_conns=50
        )

        self.embedding_index_name = OS_CONFIG[OS_CONFIG_PARA_NAME_EMBEDDING_INDEX_NAME]
        self.endpoint = OS_CONFIG[OS_CONFIG_PARA_NAME_ENDPOINT]
        self.instance_id = OS_CONFIG[OS_CONFIG_PARA_NAME_INSTANCE_ID]
        self.tableName = OS_CONFIG[OS_CONFIG_PARA_NAME_TABLE_NAME]
        self.optionsHeaders = {}

        self.ha3EngineClient = client.Client(self.osConfig)

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a dict of document_ids to list of document chunks and inserts them into the database.
        Return a list of document ids.
        """

        def _new_doc(doc_chunk: DocumentChunk) -> Dict:
            add_doc = dict()
            add_doc_fields = dict()

            add_doc_fields.__setitem__(OS_FIELDS_ID, doc_chunk.id)
            add_doc_fields.__setitem__(OS_FIELDS_TEXT, doc_chunk.text)
            add_doc_fields.__setitem__(OS_FIELDS_EMBEDDING, doc_chunk.embedding)
            add_doc_fields.__setitem__(OS_FIELDS_DOCUMENT_ID, doc_chunk.metadata.document_id)
            add_doc_fields.__setitem__(OS_FIELDS_SOURCE, doc_chunk.metadata.source)
            add_doc_fields.__setitem__(OS_FIELDS_SOURCE_ID, doc_chunk.metadata.source_id)
            add_doc_fields.__setitem__(OS_FIELDS_URL, doc_chunk.metadata.url)
            add_doc_fields.__setitem__(OS_FIELDS_AUTHOR, doc_chunk.metadata.author)
            add_doc_fields.__setitem__(OS_FIELDS_CREATED_AT, doc_chunk.metadata.created_at)

            add_doc.__setitem__("fields", add_doc_fields)
            add_doc.__setitem__("cmd", "add")
            return add_doc

        if chunks is None or chunks.values() is None:
            return []
        try:
            push_docs = []
            for document_chunks in chunks.values():
                for chunk in document_chunks:
                    push_docs.append(_new_doc(chunk))

            push_request = models.PushDocumentsRequestModel(self.optionsHeaders, push_docs)
            push_response = self.ha3EngineClient.push_documents(self.tableName, OS_FIELDS_ID, push_request)
            json_response = json.loads(push_response.body)
            if json_response["status"] == 'OK':
                return list(chunks.keys())
            return []
        except Exception as e:
            logger.error("failed to upsert chunk to alibaba cloud opensearch server endpoint:{}, tableName:{}, error: {}"
                         .format(self.endpoint, self.tableName, e))
            raise e

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:

        def generate_query(single_query: QueryWithEmbedding) -> str:
            tok_k = single_query.top_k
            tmp_search_config_str = f"config=start:0,hit:{tok_k},format:json&&cluster=general&&kvpairs=first_formula:proxima_score({self.embedding_index_name})&&sort=+RANK"
            tmp_query_str = f"&&query={self.embedding_index_name}:" + "'" + ",".join(
                str(x) for x in single_query.embedding) + "'"

            query_filter = single_query.filter
            if single_query.filter is None:
                return tmp_search_config_str + tmp_query_str

            start_date_filter = None if query_filter.start_date is None else int(
                datetime.datetime.fromisoformat(query_filter.start_date).timestamp())
            end_date_filter = None if query_filter.end_date is None else int(
                datetime.datetime.fromisoformat(query_filter.end_date).timestamp())
            conditions = [
                (OS_FIELDS_DOCUMENT_ID + "=\"{0}\"", query_filter.document_id),
                (OS_FIELDS_SOURCE_ID + "=\"{0}\"", query_filter.source_id),
                (OS_FIELDS_SOURCE + "=\"{0}\"", query_filter.source),
                (OS_FIELDS_AUTHOR + "=\"{0}\"", query_filter.author),
                (OS_FIELDS_CREATED_AT + ">={0}", start_date_filter),
                (OS_FIELDS_CREATED_AT + "<={0}", end_date_filter),
            ]

            filter_clause = "&&filter=" + " AND ".join(
                [cond[0].format(cond[1]) for cond in conditions if cond[1] is not None]
            )
            tmp_query_str += filter_clause
            return tmp_search_config_str + tmp_query_str

        def search_data(single_query_str: str):
            search_query = models.SearchQuery(query=single_query_str)
            search_request = models.SearchRequestModel(self.optionsHeaders, search_query)
            return self.ha3EngineClient.search(search_request)

        def create_results(json_result):
            items = json_result['result']['items']
            query_result_list = []
            for item in items:
                fields = item["fields"]
                document_chunk = DocumentChunkWithScore(
                    id=fields[OS_FIELDS_ID],
                    text=fields[OS_FIELDS_TEXT],
                    score=item["sortExprValues"][0],
                    metadata=DocumentChunkMetadata(
                        source=fields[OS_FIELDS_SOURCE],
                        source_id=fields[OS_FIELDS_SOURCE_ID],
                        document_id=fields[OS_FIELDS_DOCUMENT_ID],
                        url=fields[OS_FIELDS_URL],
                        created_at=datetime.datetime.fromtimestamp(int(fields[OS_FIELDS_CREATED_AT])).isoformat(),
                        author=fields[OS_FIELDS_AUTHOR],
                    ),
                )
                query_result_list.append(document_chunk)
            return query_result_list

        async def single_query(query: QueryWithEmbedding) -> QueryResult:
            try:
                query_str = generate_query(query)
                search_response = search_data(query_str)
                json_response = json.loads(search_response.body)
                if len(json_response["errors"]) != 0:
                    logger.error(f"query {self.endpoint} {self.instance_id} errors:{json_response['errors']} failed.")
                else:
                    results = create_results(json_response)
                    return QueryResult(query=query.query, results=results)
            except Exception as e:
                logger.error(
                    f"query alibaba cloud opensearch endpoint:{self.endpoint} instance_id:{self.instance_id} failed", e)
            return QueryResult(query=query.query, results=[])

        return await asyncio.gather(*(single_query(query) for query in queries))

    async def delete(
            self,
            ids: Optional[List[str]] = None,
            filter: Optional[DocumentMetadataFilter] = None,
            delete_all: Optional[bool] = None,
    ) -> bool:
        async def execute_delete(delete_doc_ids: Optional[List[str]]) -> bool:
            if len(delete_doc_ids) == 0:
                return True
            try:
                delete_doc_list = []
                for delete_doc_id in delete_doc_ids:
                    delete_doc = dict()
                    delete_doc_fields = dict()
                    delete_doc_fields.__setitem__(OS_FIELDS_ID, delete_doc_id)
                    delete_doc.__setitem__("fields", delete_doc_fields)
                    delete_doc.__setitem__("cmd", "delete")
                    delete_doc_list.append(delete_doc)

                delete_request = models.PushDocumentsRequestModel(self.optionsHeaders, delete_doc_list)
                delete_response = self.ha3EngineClient.push_documents(self.tableName, OS_FIELDS_ID, delete_request)
                json_response = json.loads(delete_response.body)
                return json_response["status"] == 'OK'
            except Exception as e:
                logger.error(
                    f"delete alibaba cloud opensearch doc failed, endpoint:{self.endpoint} instance_id:{self.instance_id}",
                    e)
                return False

        if delete_all:
            raise Exception("OpenSearch currently does not support deleting all.")
        elif ids:
            return await execute_delete(ids)
        elif filter is not None:
            raise Exception("OpenSearch currently does not support deleting based on filter conditions.")
        else:
            raise Exception("Does not support deletion operation type.")
