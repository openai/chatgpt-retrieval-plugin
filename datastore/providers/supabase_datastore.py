import os
from typing import Dict, List, Optional
from datetime import datetime

from supabase import Client

from services.date import to_unix_timestamp
from datastore.datastore import DataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
    DocumentChunkWithScore,
)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
assert SUPABASE_URL is not None, "SUPABASE_URL is not set"
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
assert SUPABASE_ANON_KEY is not None, "SUPABASE_ANON_KEY is not set"
# switch to service role key if you want this app to be able to bypass your Row Level Security policies
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

INIT_DB = bool(os.environ.get("INIT_DB", False))
PG_HOST = os.environ.get("PG_HOST")
PG_PORT = int(os.environ.get("PG_PORT", 5432))
PG_DB = os.environ.get("PG_DB", "postgres")
PG_USER = os.environ.get("PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "postgres")


# class that implements the DataStore interface for Supabase Datastore provider
class SupabaseDataStore(DataStore):
    def __init__(self):
        if INIT_DB:
            self._init_db()
        self.client = Client(SUPABASE_URL, SUPABASE_ANON_KEY)

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a dict of document_ids to list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        for document_id, document_chunks in chunks.items():
            for chunk in document_chunks:
                json = {
                    "id": chunk.id,
                    "content": chunk.text,
                    "embedding": chunk.embedding,
                    "document_id": document_id,
                    "source": chunk.metadata.source,
                    "source_id": chunk.metadata.source_id,
                    "url": chunk.metadata.url,
                    "author": chunk.metadata.author,
                }
                if chunk.metadata.created_at:
                    json["created_at"] = (
                        datetime.fromtimestamp(
                            to_unix_timestamp(chunk.metadata.created_at)
                        ),
                    )
                self.client.table("documents").upsert(json).execute()

        return list(chunks.keys())

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """
        query_results: List[QueryResult] = []
        for query in queries:
            # get the top 3 documents with the highest cosine similarity using rpc function in the database called "match_page_sections"
            params = {
                "in_embedding": query.embedding,
            }
            if query.top_k:
                params["in_match_count"] = query.top_k
            if query.filter:
                if query.filter.document_id:
                    params["in_document_id"] = query.filter.document_id
                if query.filter.source:
                    params["in_source"] = query.filter.source.value
                if query.filter.source_id:
                    params["in_source_id"] = query.filter.source_id
                if query.filter.author:
                    params["in_author"] = query.filter.author
                if query.filter.start_date:
                    params["in_start_date"] = datetime.fromtimestamp(
                        to_unix_timestamp(query.filter.start_date)
                    )
                if query.filter.end_date:
                    params["in_end_date"] = datetime.fromtimestamp(
                        to_unix_timestamp(query.filter.end_date)
                    )
            try:
                response = self.client.rpc(
                    "match_page_sections", params=params
                ).execute()
                data = response.data
                results: List[DocumentChunkWithScore] = []
                for row in data:
                    document_chunk = DocumentChunkWithScore(
                        id=row["id"],
                        text=row["content"],
                        # TODO: add embedding to the response ?
                        # embedding=row["embedding"],
                        score=float(row["similarity"]),
                        metadata=DocumentChunkMetadata(
                            source=row["source"],
                            source_id=row["source_id"],
                            document_id=row["document_id"],
                            url=row["url"],
                            created_at=row["created_at"],
                            author=row["author"],
                        ),
                    )
                    results.append(document_chunk)
                query_results.append(QueryResult(query=query.query, results=results))
            except Exception as e:
                print("error:", e)
                query_results.append(QueryResult(query=query.query, results=[]))
        return query_results

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes vectors by ids, filter, or everything in the datastore.
        Multiple parameters can be used at once.
        Returns whether the operation was successful.
        """
        if delete_all:
            try:
                self.client.table("documents").delete().like(
                    "document_id", "%"
                ).execute()
            except:
                return False
        elif ids:
            try:
                self.client.table("documents").delete().in_(
                    "document_id", ids
                ).execute()
            except:
                return False
        elif filter:
            try:
                builder = self.client.table("documents").delete()
                if filter.document_id:
                    builder = builder.lte(
                        "document_id",
                        filter.document_id,
                    )
                if filter.source:
                    builder = builder.eq("source", filter.source)
                if filter.source_id:
                    builder = builder.eq("source_id", filter.source_id)
                if filter.author:
                    builder = builder.eq("author", filter.author)
                if filter.start_date:
                    builder = builder.gte(
                        "created_at",
                        datetime.fromtimestamp(to_unix_timestamp(filter.start_date)),
                    )
                if filter.end_date:
                    builder = builder.lte(
                        "created_at",
                        datetime.fromtimestamp(to_unix_timestamp(filter.end_date)),
                    )
                builder.execute()
            except:
                return False
        return True

    def _init_db():
        from psycopg2 import connect

        with connect(
            dbname=PG_DB, user=PG_USER, password=PG_PASSWORD, host=PG_HOST, port=PG_PORT
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                          create extension if not exists pgvector with schema extensions;
                          """
                )

                cur.execute(
                    """
                          create table if not exists documents (
                            id text primary key default uuid_generate_v4()::text,
                            source text,
                            source_id text,
                            content text,
                            document_id text,
                            author text,
                            url text,
                            created_at timestamptz default now(),
                            embedding vector(1536)
                          );
                          """
                )

                cur.execute(
                    """
                          create or replace function match_page_sections(in_embedding vector(1536)
                                                                       , in_match_count int default 3
                                                                       , in_document_id text default '%%'
                                                                       , in_source_id text default '%%'
                                                                       , in_source text default '%%'
                                                                       , in_author text default '%%'
                                                                       , in_start_date timestamptz default '-infinity'
                                                                       , in_end_date timestamptz default 'infinity')
                          returns table (source text
                                       , source_id text
                                       , document_id text
                                       , url text
                                       , created_at timestamptz
                                       , author text
                                       , content text
                                       , embedding vector(1536)
                                       , similarity float)
                          language plpgsql
                          as $$
                          #variable_conflict use_variable
                          begin
                            return query
                            select
                              documents.source,
                              documents.source_id,
                              documents.document_id,
                              documents.url,
                              documents.created_at,
                              documents.author,
                              documents.content,
                              documents.embedding,
                              (documents.embedding <#> in_embedding) * -1 as similarity
                            from documents

                            where in_start_date <= documents.created_at and 
                              documents.created_at <= in_end_date and
                              (documents.source_id like in_source_id or documents.source_id is null) and
                              (documents.source like in_source or documents.source is null) and
                              (documents.author like in_author or documents.author is null) and
                              (documents.document_id like in_document_id or documents.document_id is null)

                            order by documents.embedding <#> in_embedding
                            
                            limit in_match_count;
                          end;
                          $$;
                          """
                )
                conn.commit()
