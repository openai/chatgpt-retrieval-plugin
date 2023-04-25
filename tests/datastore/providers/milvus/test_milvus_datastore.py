# from pathlib import Path
# from dotenv import find_dotenv, load_dotenv
# env_path = Path(".") / "milvus.env"
# load_dotenv(dotenv_path=env_path, verbose=True)

import pytest
from models.models import (
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    DocumentChunk,
    QueryWithEmbedding,
    Source,
)
from datastore.providers.milvus_datastore import (
    OUTPUT_DIM,
    MilvusDataStore,
)


@pytest.fixture
def milvus_datastore():
    return MilvusDataStore(consistency_level = "Strong")


def sample_embedding(one_element_poz: int):
    embedding = [0] * OUTPUT_DIM
    embedding[one_element_poz % OUTPUT_DIM] = 1
    return embedding

def sample_embeddings(num: int, one_element_start: int = 0):
    # since metric type is consine, we create vector contains only one element 1, others 0
    embeddings = []
    for x in range(num):
        embedding = [0] * OUTPUT_DIM
        embedding[(x + one_element_start) % OUTPUT_DIM] = 1
        embeddings.append(embedding)
    return embeddings

@pytest.fixture
def document_chunk_one():
    doc_id = "zerp"
    doc_chunks = []

    ids = ["abc_123", "def_456", "ghi_789"]
    texts = [
        "lorem ipsum dolor sit amet",
        "consectetur adipiscing elit",
        "sed do eiusmod tempor incididunt",
    ]
    sources = [Source.email, Source.file, Source.chat]
    source_ids = ["foo", "bar", "baz"]
    urls = ["foo.com", "bar.net", "baz.org"]
    created_ats = [
        "1929-10-28T09:30:00-05:00",
        "2009-01-03T16:39:57-08:00",
        "2021-01-21T10:00:00-02:00",
    ]
    authors = ["Max Mustermann", "John Doe", "Jane Doe"]

    embeddings = sample_embeddings(len(texts))

    for i in range(3):
        chunk = DocumentChunk(
            id=ids[i],
            text=texts[i],
            metadata=DocumentChunkMetadata(
                document_id=doc_id,
                source=sources[i],
                source_id=source_ids[i],
                url=urls[i],
                created_at=created_ats[i],
                author=authors[i],
            ),
            embedding=embeddings[i],  # type: ignore
        )

        doc_chunks.append(chunk)

    return {doc_id: doc_chunks}


@pytest.fixture
def document_chunk_two():
    doc_id_1 = "zerp"
    doc_chunks_1 = []

    ids = ["abc_123", "def_456", "ghi_789"]
    texts = [
        "1lorem ipsum dolor sit amet",
        "2consectetur adipiscing elit",
        "3sed do eiusmod tempor incididunt",
    ]
    sources = [Source.email, Source.file, Source.chat]
    source_ids = ["foo", "bar", "baz"]
    urls = ["foo.com", "bar.net", "baz.org"]
    created_ats = [
        "1929-10-28T09:30:00-05:00",
        "2009-01-03T16:39:57-08:00",
        "3021-01-21T10:00:00-02:00",
    ]
    authors = ["Max Mustermann", "John Doe", "Jane Doe"]
    embeddings = sample_embeddings(len(texts))

    for i in range(3):
        chunk = DocumentChunk(
            id=ids[i],
            text=texts[i],
            metadata=DocumentChunkMetadata(
                document_id=doc_id_1,
                source=sources[i],
                source_id=source_ids[i],
                url=urls[i],
                created_at=created_ats[i],
                author=authors[i],
            ),
            embedding=embeddings[i],  # type: ignore
        )

        doc_chunks_1.append(chunk)

    doc_id_2 = "merp"
    doc_chunks_2 = []

    ids = ["jkl_123", "lmn_456", "opq_789"]
    texts = [
        "3sdsc efac feas sit qweas",
        "4wert sdfas fdsc",
        "52dsc fdsf eiusmod asdasd incididunt",
    ]
    sources = [Source.email, Source.file, Source.chat]
    source_ids = ["foo", "bar", "baz"]
    urls = ["foo.com", "bar.net", "baz.org"]
    created_ats = [
        "4929-10-28T09:30:00-05:00",
        "5009-01-03T16:39:57-08:00",
        "6021-01-21T10:00:00-02:00",
    ]
    authors = ["Max Mustermann", "John Doe", "Jane Doe"]
    embeddings = sample_embeddings(len(texts), 3)

    for i in range(3):
        chunk = DocumentChunk(
            id=ids[i],
            text=texts[i],
            metadata=DocumentChunkMetadata(
                document_id=doc_id_2,
                source=sources[i],
                source_id=source_ids[i],
                url=urls[i],
                created_at=created_ats[i],
                author=authors[i],
            ),
            embedding=embeddings[i],  # type: ignore
        )

        doc_chunks_2.append(chunk)

    return {doc_id_1: doc_chunks_1, doc_id_2: doc_chunks_2}


@pytest.mark.asyncio
async def test_upsert(milvus_datastore, document_chunk_one):
    await milvus_datastore.delete(delete_all=True)
    res = await milvus_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    milvus_datastore.col.flush()
    assert 3 == milvus_datastore.col.num_entities
    milvus_datastore.col.drop()


@pytest.mark.asyncio
async def test_reload(milvus_datastore, document_chunk_one, document_chunk_two):
    await milvus_datastore.delete(delete_all=True)

    res = await milvus_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    milvus_datastore.col.flush()
    assert 3 == milvus_datastore.col.num_entities

    new_store = MilvusDataStore()
    another_in = {i: document_chunk_two[i] for i in document_chunk_two if i != res[0]}
    res = await new_store._upsert(another_in)
    new_store.col.flush()
    assert 6 == new_store.col.num_entities
    query = QueryWithEmbedding(
        query="lorem",
        top_k=10,
        embedding=sample_embedding(0),
    )
    query_results = await milvus_datastore._query(queries=[query])
    assert 1 == len(query_results)
    new_store.col.drop()


@pytest.mark.asyncio
async def test_upsert_query_all(milvus_datastore, document_chunk_two):
    await milvus_datastore.delete(delete_all=True)
    res = await milvus_datastore._upsert(document_chunk_two)
    assert res == list(document_chunk_two.keys())
    milvus_datastore.col.flush()

    # Num entities currently doesn't track deletes
    query = QueryWithEmbedding(
        query="lorem",
        top_k=10,
        embedding=sample_embedding(0),
    )
    query_results = await milvus_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 6 == len(query_results[0].results)
    milvus_datastore.col.drop()


@pytest.mark.asyncio
async def test_query_accuracy(milvus_datastore, document_chunk_one):
    await milvus_datastore.delete(delete_all=True)
    res = await milvus_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    milvus_datastore.col.flush()
    query = QueryWithEmbedding(
        query="lorem",
        top_k=1,
        embedding=sample_embedding(0),
    )
    query_results = await milvus_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 1 == len(query_results[0].results)
    assert 1.0 == query_results[0].results[0].score
    assert "abc_123" == query_results[0].results[0].id
    milvus_datastore.col.drop()


@pytest.mark.asyncio
async def test_query_filter(milvus_datastore, document_chunk_one):
    await milvus_datastore.delete(delete_all=True)
    res = await milvus_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    milvus_datastore.col.flush()
    query = QueryWithEmbedding(
        query="lorem",
        top_k=1,
        embedding=sample_embedding(0),
        filter=DocumentMetadataFilter(
            start_date="2000-01-03T16:39:57-08:00", end_date="2010-01-03T16:39:57-08:00"
        ),
    )
    query_results = await milvus_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 1 == len(query_results[0].results)
    assert 1.0 != query_results[0].results[0].score
    assert "def_456" == query_results[0].results[0].id
    milvus_datastore.col.drop()


@pytest.mark.asyncio
async def test_delete_with_date_filter(milvus_datastore, document_chunk_one):
    await milvus_datastore.delete(delete_all=True)
    res = await milvus_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    milvus_datastore.col.flush()
    await milvus_datastore.delete(
        filter=DocumentMetadataFilter(
            end_date="2009-01-03T16:39:57-08:00",
        )
    )

    query = QueryWithEmbedding(
        query="lorem",
        top_k=9,
        embedding=sample_embedding(0),
    )
    query_results = await milvus_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 1 == len(query_results[0].results)
    assert "ghi_789" == query_results[0].results[0].id
    milvus_datastore.col.drop()


@pytest.mark.asyncio
async def test_delete_with_source_filter(milvus_datastore, document_chunk_one):
    await milvus_datastore.delete(delete_all=True)
    res = await milvus_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    milvus_datastore.col.flush()
    await milvus_datastore.delete(
        filter=DocumentMetadataFilter(
            source=Source.email,
        )
    )

    query = QueryWithEmbedding(
        query="lorem",
        top_k=9,
        embedding=sample_embedding(0),
    )
    query_results = await milvus_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 2 == len(query_results[0].results)
    assert "def_456" == query_results[0].results[0].id
    milvus_datastore.col.drop()


@pytest.mark.asyncio
async def test_delete_with_document_id_filter(milvus_datastore, document_chunk_one):
    await milvus_datastore.delete(delete_all=True)
    res = await milvus_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    milvus_datastore.col.flush()
    await milvus_datastore.delete(
        filter=DocumentMetadataFilter(
            document_id=res[0],
        )
    )
    query = QueryWithEmbedding(
        query="lorem",
        top_k=9,
        embedding=sample_embedding(0),
    )
    query_results = await milvus_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 0 == len(query_results[0].results)
    milvus_datastore.col.drop()


@pytest.mark.asyncio
async def test_delete_with_document_id(milvus_datastore, document_chunk_one):
    await milvus_datastore.delete(delete_all=True)
    res = await milvus_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    milvus_datastore.col.flush()
    await milvus_datastore.delete([res[0]])

    query = QueryWithEmbedding(
        query="lorem",
        top_k=9,
        embedding=sample_embedding(0),
    )
    query_results = await milvus_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 0 == len(query_results[0].results)
    milvus_datastore.col.drop()


# if __name__ == '__main__':
#     import sys
#     import pytest
#     pytest.main(sys.argv)
