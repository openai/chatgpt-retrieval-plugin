import os
from typing import Dict, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Index, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from datastore.datastore import DataStore
from models.models import (
    Document,
    DocumentChunk,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
)

Base = declarative_base()

# Read environment variables for pgvector configuration
PGVECTOR_COLLECTION = os.getenv("PGVECTOR_COLLECTION", "documents")
PGVECTOR_URL = os.getenv("PGVECTOR_URL")


class VectorDocument(DataStore):
    __tablename__ = PGVECTOR_COLLECTION

    id = Column(String, primary_key=True)
    document_id = Column(String)
    text = Column(String)
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
                    vector_doc = VectorDocument(
                        id=chunk.id,
                        document_id=document_id,
                        text=chunk.text,
                        embedding=chunk.embedding,
                    )
                    session.merge(vector_doc)

            session.commit()

        return list(chunks.keys())

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        with self.session_factory() as session:
            results = []
            for query in queries:
                query_embedding = query.embedding
                stmt = (
                    select(VectorDocument)
                    .order_by(VectorDocument.embedding.cosine_distance(query_embedding))
                    .limit(query.top_k)
                )
                matched_documents = session.execute(stmt)
                matched_documents = matched_documents.scalars().all()

                # Calculate cosine similarity from cosine distance
                query_results = [
                    {
                        "document_id": doc.document_id,
                        "text": doc.text,
                        "score": 1 - doc.embedding.cosine_distance(query_embedding),
                    }
                    for doc in matched_documents
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
            stmt = select(VectorDocument)

            if ids:
                stmt = stmt.where(VectorDocument.id.in_(ids))

            if filter and filter.document_id:
                stmt = stmt.where(VectorDocument.document_id == filter.document_id)

            if delete_all:
                stmt = stmt.where(True)

            result = session.execute(stmt)
            vector_documents = result.scalars().all()

            for vector_document in vector_documents:
                session.delete(vector_document)

            session.commit()

        return True
