import json
import os
import asyncio
import pandas as pd
import numpy as np


from loguru import logger
from typing import Any, Dict, List, Optional
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

try:
    import pykx as kx
    print('PyKX version: ' + kx.__version__)

except ImportError:
    raise ValueError(
        "Could not import pykx python package. "
        "Please add it to the dependencies."
    )

try:
    ## New for kdbai_client
    import kdbai_client as kdbai
    print('KDBAI-CLIENT version: ' + kdbai.__version__)
    ##

except ImportError:
    raise ValueError(
        "Could not import kdbai python package. "
        "Please add it to the dependencies."
    )




# DEFAULT_EMBEDDING_MODEL = 'text-embedding-ada-002'

# The name of the table
KDBAI_COLLECTION = os.environ.get("KDBAI_COLLECTION", "openaiEmbeddings")

# Directory where conversation memory is saved (?)
KDBAI_PERSISTENCE_DIR = os.environ.get("KDBAI_PERSISTENCE_DIR", "openai")

# Not needed?
KDBAI_INDEX_PARAMS = os.environ.get("KDBAI_INDEX_PARAMS", None)   # {"efConstruction": 8, "efSearch": 8, "M": 32}

# Not needed?
KDBAI_SEARCH_PARAMS = os.environ.get("KDBAI_SEARCH_PARAMS")

# Algorithm/index for vector similarity search
DEFAULT_ALGORITHM = os.environ.get("DEFAULT_ALGORITHM")

# HNSW's Default Parameters
DEFAULT_EFCONSTRUCTION = 8 
DEFAULT_M = 32

DEFAULT_DIM = 1536
UPSERT_BATCH_SIZE = 100
KDBAI_VECTOR_COL_NAME = "vecs"


schema = dict(
    columns=[
        dict(
            name='vecs', 
            vectorIndex=
                dict(
                    type='flat', 
                    metric='L2', 
                    dims=DEFAULT_DIM
                    )
            ),
        dict(
            name='source', 
            pytype='bytes'
            ),
        dict(
            name='source_id', 
            pytype='str'
            ),
        dict(
            name='url', 
            pytype='bytes'
            ),
        dict(
            name='created_at', 
            pytype='datetime64[ns]'
            ),
        dict(
            name='author', 
            pytype='bytes'
            ),
        dict(
            name='document_id', 
            pytype='str'
            ),
        dict(
            name='text', 
            pytype='bytes'
            ),
        dict(
            name='chunk_id', 
            pytype='str'
            )
        ]
    ) 


class KDBAIDataStore(DataStore):

    def __init__(
        self,
        # name of the collection of embeddings 
        index_name: str = KDBAI_COLLECTION,
        
        # where conversation memory is saved
        # persist_directory: Optional[str] = KDBAI_PERSISTENCE_DIR,
        
        # manually input the index params (algorithm, metric, dimensions etc)
        # options: Optional[str] = KDBAI_INDEX_PARAMS
    ) -> None: 
        
        self._index_name = index_name 
        
        # self._persist_directory = persist_directory
        # self._options = options

        # self.search_params = KDBAI_SEARCH_PARAMS or None
        
        try:
                        
            # NEW KDBAI-CLIENT
            
            # create a new session
            print('Creating kdbai Session...')
            session = kdbai.Session(host='localhost', port=8082, protocol='http')
            print("Tables in current session:")
            print(session.list())  

            # create a vector database table using the schema
            print('Getting table:')
            name = 'testingupsert1'
            
            try:
                self._table = session.create_table(name, schema)
            except:
                self._table = session.table(name)
            
            
            print('Session tables:')
            print(session.list())
            
            print('Table schema:')
            print(self._table.schema())
        
        except Exception as e:
            logger.error(f"Error in creating table: {e}")
            raise e

        return None

        
    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """Upsert chunks into the datastore.

        Args:
            chunks (Dict[str, List[DocumentChunk]]): A list of DocumentChunks to insert

        Raises:
            e: Error in upserting data.

        Returns:
            List[str]: The document_id's that were inserted.
        """

        # Initialize a list of ids to return
        try: 
            doc_ids: List[str] = []
            
            # Initialize a list of vectors to upsert
            vecs = []
            # Loop through the dict items
            for doc_id, chunk_list in chunks.items():
                # Append the id to the ids list
                
                print(f"doc_id: {doc_id}")
                print(f"chunk_list: {chunk_list}")
                
                doc_ids.append(doc_id)
                logger.info(f"Upserting document_id: {doc_id}")
                
                for chunk in chunk_list:
                    
                    print(f"chunk: {chunk}")
                    
                    # Create a vector tuple of (id, embedding, metadata)
                    # Convert the metadata object to a dict with unix timestamps for dates
                    self._metadata = self._kdbai_metadata(chunk.metadata) # chunk.metadata comes from retrieval app

                    # Add the text and document id to the metadata DICT
                    self._metadata["text"] = chunk.text
                    self._metadata["document_id"] = doc_id
                    self._metadata["chunk_id"] = chunk.id
                    
                    vec = (chunk.embedding, self._metadata)
                    vecs.append(vec)

            # Slice up our insert data into batches
            batches = [
                vecs[i : i + UPSERT_BATCH_SIZE]
                for i in range(0, len(vecs), UPSERT_BATCH_SIZE)
            ]

            for batch in batches:
                
                # generates an embedding vector for each item in batch
                embeddings = np.array([t[0] for t in batch]) # vec[0]   
                print("Shape of embeddings vector: ", embeddings.shape)

                df = pd.DataFrame(dict(vecs=list(embeddings)))
                
                # extracts each metadata item in batch to DataFrame
                new_meta_df = pd.DataFrame([t[1] for t in batch]) # vec[1]
                
                print("DataFrame columns: ", new_meta_df.columns)
                
                for col in new_meta_df.columns:
                    df[col] = new_meta_df[col]

                try:
                    logger.info(f"Upserting batch of size {len(batch[0])}")

                    print("Inserting DataFrame:")
                    print(df)  
                        
                    self._table.insert(df)
                    
                    logger.info(f"Upserted batch successfully")

                except Exception as e:
                    logger.error(f"Failed to insert batch records, error: {e}")
                    raise e
                    
            return doc_ids
        
        except Exception as e:
            logger.error("Insert to collection failed, error: {}".format(e))
            return []


    def _kdbai_metadata(
        self, metadata: Optional[DocumentChunkMetadata] = None
    ) -> Dict[str, Any]:
        if metadata is None:
            return {}

        kdbai_metadata = {}

        for key, value in metadata.dict().items():
            if value is not None:
                if key in ["created_at"]:
                    kdbai_metadata["created_at"] = to_unix_timestamp(value)
                else:
                    kdbai_metadata[key] = value

        return kdbai_metadata


    ## QUERY vs SEARCH
    async def _query(
        self,
        queries: List[QueryWithEmbedding], # a list of embedded query vectors 
    ) -> List[QueryResult]:
        """Query

        Search the embedding and its filter in the collection.

        Args:
            queries (List[QueryWithEmbedding]): The list of searches to perform.

        Returns:
            List[QueryResult]: Results for each search.
        """

        # handle each query vector at a time
        async def _single_query(query: QueryWithEmbedding) -> QueryResult:

            try:
                
                # if there are no filters, just return the n nearest neighbours and their ids 
                if query.filter is None:
                    
                    # calls search() function from kdbai.Index()
                    #   Input: a batch of query vectors and a number of nearest records to search
                    #   Output: a tuple with 2D Numpy arrays containing the distances and IDs of nearest vectors
                    #dist, ids = self._index.search(np.array([query.embedding]).astype('float32'), k=query.top_k)
                    
                    # NEW KDBAI-CLIENT
                    search_results = self._table.search(dict(vectors=np.array([query.embedding]).astype('float32'), n=query.top_k))
                    dist = search_results["__nn_distance"]
                    ids = search_results["id"]
                    
                
                # HANDLE CASES WHERE WE WANT TO FILTER THE RESULTS (see bottom of file for params here)

                # else:
                #     whereDict = query.filter.dict()

                #     if len(whereDict.keys()) > 1:
                #         raise ValueError("Only 1 filter is allowed currently.")

                #     filterStr = "\""+(''.join([str(list(x)[0]) for x in [whereDict.keys(), whereDict.values()]]))+"\""
                #     responses = self._index.filtered_search(np.array([query.embedding]).astype('float32'), filterStr, verbose=1, options=dict(neighbors=query.top_k)).pd()
                
            except Exception as e:
                logger.error(f"Error querying index: {e}")
                raise e

            global table
            query_results: List[DocumentChunkWithScore] = []
            
            # iterate through the query results
            for dist, id in zip(dist[0],ids[0]):

                indices  = id
                score    = dist
                text     = table.loc[table.index == id]["text"].values[0]

                metadata = table.drop(['vecs','text'],axis=1).loc[table.index == id].squeeze().to_dict()

                # If the source is not a valid Source in the Source enum, set it to None
                if (
                    metadata
                    and "source" in metadata
                    and metadata["source"] not in Source.__members__
                ):
                    metadata["source"] = None

                # Create a document chunk with score object with the result data
                result = DocumentChunkWithScore(
                    id=indices,
                    score=score,
                    text=text,
                    metadata=metadata,
                )
                query_results.append(result)
                
            return QueryResult(query=query.query, results=query_results)
        
        
        # iterate through each query and gather results
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
        
        # If deleting all, drop collection
        try:
            if delete_all:
                
                # NEW KDBAI-CLIENT  
                self._table.drop()  
                         
                # table = table.head(0)
            else:
                logger.error("Functionality is not implemented yet")
            
            return True

        except Exception as e:
            logger.error("Failed to insert records, error: {}".format(e))
            return []


## query = dict(labels=dict(region, assetClass),
#               startTS, endTS, inputTZ, outputTZ,
#               filter, groupBy, agg, temporality, sortCols)