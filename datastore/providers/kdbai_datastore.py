import os
from typing import Dict, List, Optional

from loguru import logger
import pandas as pd

from services.date import to_unix_timestamp
from datastore.datastore import DataStore

from models.models import (
    DocumentChunk,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
)

try:
    import pykx as kx
    logger.info('PyKX version: ' + kx.__version__)

except ImportError:
    raise ValueError(
        'Could not import pykx package.'
        'Please add it to the dependencies.'
    )

try:
    import kdbai_client as kdbai
    logger.info('KDBAI client version: ' + kdbai.__version__)

except ImportError:
    raise ValueError(
        'Could not import kdbai_client package.'
        'Please add it to the dependencies.'
    )


KDBAI_ENDPOINT = os.environ.get('KDBAI_ENDPOINT', 'http://localhost:8082')
KDBAI_API_KEY = os.environ.get('KDBAI_API_KEY', '')

if KDBAI_API_KEY == '':
    KDBAI_API_KEY = None

DEFAULT_DIMS = 1536
BATCH_SIZE = 100

DEFAULT_SCHEMA = dict(
    columns=[
        dict(name='document_id', pytype='str'),
        dict(name='text', pytype='bytes'),
        dict(name='vecs', vectorIndex=dict(type='flat', metric='L2', dims=DEFAULT_DIMS)),
    ])

SCHEMA = os.environ.get('KDBAI_SCHEMA', DEFAULT_SCHEMA)
TABLE = os.environ.get('KDBAI_TABLE', 'documents')


class KDBAIDataStore(DataStore):

    def __init__(self) -> None: 
        try:
            logger.info('Creating KDBAI datastore...')
            self._session = kdbai.Session(endpoint=KDBAI_ENDPOINT, api_key=KDBAI_API_KEY)
            
            if TABLE in self._session.list():
                self._table = self._session.table(TABLE)
            else:
                self._table = self._session.create_table(TABLE, SCHEMA)
                    
        except Exception as e:
            logger.error(f'Error while initializing KDBAI datastore: {e}.')
            raise e
        
        
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
            docs = []
            for doc_id, chunk_list in chunks.items():
                for chunk in chunk_list:
                    docs.append(dict(
                        document_id=doc_id,
                        text=chunk.text,
                        vecs=chunk.embedding,
                    ))
            df = pd.DataFrame(docs)

            for i in range((len(df)-1)//BATCH_SIZE+1):
                batch = df.iloc[i*BATCH_SIZE:(i+1)*BATCH_SIZE]
                try:
                    self._table.insert(batch, warn=False)
                except Exception as e:
                    logger.exception('Failed to insert the batch of documents into the data store.')

            return list(df['document_id'])
        
        except Exception as e:
            logger.exception(f'Failed to insert documents into the data store.')
            return []


    async def _query(
        self,
        queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """Query

        Search the embedding and its filter in the collection.

        Args:
            queries (List[QueryWithEmbedding]): The list of searches to perform.

        Returns:
            List[QueryResult]: Results for each search.
        """
        out = []
        for query in queries:
            try:
                resdf = self._table.search(vectors=[query.embedding], n=query.top_k)[0]
            except Exception as e:
                logger.exception(f"Error while processing queries.")
                raise e
            
            docs = []
            for result in resdf.to_dict(orient='record'):
                docs.append(DocumentChunkWithScore(
                    id=result['document_id'],
                    text=result['text'],
                    metadata=dict(),
                    score=result['__nn_distance'],
                ))
            out.append(QueryResult(query=query.query, results=docs))

        return out


    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        
        """
        Removes vectors by ids, filter, or everything from the index.
        """
        # Delete all vectors and assosiated index

        try:
           if delete_all:
                self._table.drop()
                logger.info(f"Deleted all vectors successfully")
                return True
           else:
                logger.error("Functionality is not implemented yet")
		
        except Exception as e:
            logger.error("Failed to delete records, error: {}".format(e))
            return []

