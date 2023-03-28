import os
from typing import Dict, List, Optional, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Index, String, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import asc, and_
from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker, declarative_base

from datastore.datastore import DataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
)

Base = declarative_base()

# Read environment variables for pgvector configuration
PGVECTOR_COLLECTION = os.getenv("PGVECTOR_COLLECTION", "documents")
PGVECTOR_URL = os.getenv("PGVECTOR_URL")


class VectorDocumentChunk(Base):
    __tablename__ = PGVECTOR_COLLECTION

    id = Column(String, primary_key=True)
    document_id = Column(String, index=True)
    text = Column(String)
    metadata_ = Column("metadata", JSONB)
    embedding = Column(Vector(1536))

    # Add a Cosine Distance index for faster querying
    index = Index(
        "vector_cosine_idx",
        embedding,
        postgresql_using="ivfflat",
        postgresql_ops={"embedding": "vector_cosine_ops", "lists": "100"},
    )


class PgVectorDataStore(DataStore):
    def __init__(self):
        # Read the database URL from the PGVECTOR_URL environment variable
        if not PGVECTOR_URL:
            raise ValueError("PGVECTOR_URL environment variable is not set")

        self.engine = create_engine(PGVECTOR_URL)
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine)

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        with self.session_factory() as session:
            for document_id, document_chunks in chunks.items():
                for chunk in document_chunks:
                    vector_doc = VectorDocumentChunk(
                        id=chunk.id,
                        document_id=document_id,
                        text=chunk.text,
                        metadata_=chunk.metadata.dict(),
                        embedding=chunk.embedding,
                    )
                    session.merge(vector_doc)

            session.commit()

        return list(chunks.keys())

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        with self.session_factory() as session:
            results = []
            for query in queries:
                embedding_filter = VectorDocumentChunk.embedding.cosine_distance(query.embedding).label("distance")

                metadata_filter = self._metadata_filter(query.filter)
                query_filters = and_(embedding_filter, *metadata_filter)
                
                query_results = (
                    session.query(VectorDocumentChunk)
                    .filter_by(**query_filters)
                    .order_by(asc("distance"))
                    .limit(query.top_k)
                    .all()
                )
                
                # Calculate cosine similarity from cosine distance
                query_results = [
                    DocumentChunkWithScore(
                        id=doc.id,
                        text=doc.text,
                        metadata=DocumentChunkMetadata(**doc.metadata),
                        score=1 - doc.embedding.cosine_distance(query.embedding),
                    )
                    for doc in query_results
                ]

                results.append(QueryResult(query=query.query, results=query_results))

            return results

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        with self.session_factory() as session:
            stmt = delete(VectorDocumentChunk)

            if ids:
                stmt = stmt.where(VectorDocumentChunk.document_id.in_(ids))

            if filter:
                stmt_filters = self._metadata_filter(filter)
            
                if filter.document_id:
                    stmt_filters = and_(VectorDocumentChunk.document_id == filter.document_id, *stmt_filters)

            stmt = stmt.where(stmt_filters)

            if delete_all:
                stmt = stmt.where(True)

            session.execute(stmt)
            session.commit()

        return True

    def _metadata_filter(
        self, filter: Optional[DocumentMetadataFilter] = None
    ) -> Dict[str, Any]:
        if filter is None:
            return {}

        metadata_filter = {}

        # For each field in the MetadataFilter, check if it has a value and add the corresponding filter expression
        for key, value in filter.dict().items():
            if value is not None:
                metadata_filter.append(VectorDocumentChunk.metadata_[key].astext == str(value))

        return metadata_filter