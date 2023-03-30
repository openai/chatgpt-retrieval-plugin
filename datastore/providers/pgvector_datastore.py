import os
from typing import Any, Dict, List, Optional

from pgvector.sqlalchemy import Vector  # type: ignore
from sqlalchemy import Column, Index, String, and_, asc, create_engine, delete
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, sessionmaker

from datastore.datastore import DataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
    Source,
)

Base = declarative_base()  # type: Any

# Read environment variables for pgvector configuration
PGVECTOR_COLLECTION = os.getenv("PGVECTOR_COLLECTION", "documents")
PGVECTOR_URL = os.getenv("PGVECTOR_URL")


class VectorDocumentChunk(Base):
    __tablename__ = PGVECTOR_COLLECTION

    id = Column(String, primary_key=True)
    document_id = Column(String, index=True)
    text = Column(String)
    metadata_ = Column("metadata", JSONB)
    embedding = Column(Vector(1536))  # type: ignore

    # Add a Cosine Distance index for faster querying
    index = Index(
        "vector_cosine_idx",
        embedding,
        postgresql_using="ivfflat",
        postgresql_ops={"embedding": "vector_cosine_ops", "lists": "100"},
    )


class PgVectorDataStore(DataStore):
    def __init__(self, recreate_collection: bool = False):
        # Read the database URL from the PGVECTOR_URL environment variable
        if not PGVECTOR_URL:
            raise ValueError("PGVECTOR_URL environment variable is not set")

        self.engine = create_engine(PGVECTOR_URL, echo=False)
        if recreate_collection:
            Base.metadata.drop_all(bind=self.engine)
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
                metadata_filters = self._metadata_filter(query.filter)

                query_results = (
                    session.query(
                        VectorDocumentChunk,
                        VectorDocumentChunk.embedding.cosine_distance(
                            query.embedding
                        ).label("distance"),
                    )
                    .filter(*metadata_filters)
                    .order_by(asc("distance"))
                    .limit(query.top_k)
                    .all()
                )

                # Calculate cosine similarity from cosine distance
                query_results = [
                    DocumentChunkWithScore(
                        id=result.VectorDocumentChunk.id,
                        text=result.VectorDocumentChunk.text,
                        metadata=DocumentChunkMetadata(
                            **result.VectorDocumentChunk.metadata_
                        ),
                        score=1 - result.distance,
                    )
                    for result in query_results
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
                    stmt_filters = and_(
                        VectorDocumentChunk.document_id == filter.document_id,
                        *stmt_filters
                    )

                stmt = stmt.where(*stmt_filters)

            if delete_all:
                stmt = stmt.where(True)

            session.execute(stmt)
            session.commit()

        return True

    def _metadata_filter(
        self, filter: Optional[DocumentMetadataFilter] = None
    ) -> List[Any]:
        if filter is None:
            return []

        # For each field in the MetadataFilter, check if it has a value and add the corresponding filter expression
        return [
            (
                VectorDocumentChunk.metadata_["created_at"].astext >= value
                if key == "start_date"
                else VectorDocumentChunk.metadata_["created_at"].astext <= value
                if key == "end_date"
                else VectorDocumentChunk.metadata_[key].astext == Source[value]
                if key == "source"
                else VectorDocumentChunk.metadata_[key].astext == str(value)
            )
            for key, value in filter.dict().items()
            if value is not None
        ]
