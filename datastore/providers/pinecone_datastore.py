import os
import openai
import json
from typing import Any, Dict, List, Optional
import pinecone
from tenacity import retry, wait_random_exponential, stop_after_attempt
import asyncio
from algoliasearch.search_client import SearchClient

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
from services.date import to_unix_timestamp

# Read environment variables for Pinecone configuration
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT")
PINECONE_INDEX = os.environ.get("PINECONE_INDEX")
assert PINECONE_API_KEY is not None
assert PINECONE_ENVIRONMENT is not None
assert PINECONE_INDEX is not None

# Initialize Pinecone with the API key and environment
pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)

# Set the batch size for upserting vectors to Pinecone
UPSERT_BATCH_SIZE = 100

ALGOLIA_ADMIN_API_KEY = os.environ.get("ALGOLIA_ADMIN_API_KEY")
ALGOLIA_APP_ID = os.environ.get("ALGOLIA_APP_ID")
ALGOLIA_JOB_INDEX = os.environ.get("ALGOLIA_JOB_INDEX")
assert ALGOLIA_ADMIN_API_KEY is not None
assert ALGOLIA_APP_ID is not None
assert ALGOLIA_JOB_INDEX is not None

algolia_job_index = SearchClient.create(ALGOLIA_APP_ID, ALGOLIA_ADMIN_API_KEY).init_index(ALGOLIA_JOB_INDEX)

algolia_attributes_to_retrieve = [
    'objectID',
    'hospitalName',
    'nurseflyDiscipline',
    'nurseflySpecialty',
    'specialtyNames',
    'hospitalCity',
    'hospitalState',
    'startDate',
    'seniority',
    'days',
    'evenings',
    'nights',
    'hoursPerWeek',
    'contractLength',
    'message',
    'description',
    'searchDescription',
    'searchTitle',
    'location',
    'employerBenefits',
    'shiftFilter',
    'pay',
    'rawData',
]

algolia_object_shape = json.dumps({
    "employerBenefits": [],
    "hospitalName": "",
    "hospitalAddress": "",
    "hospitalZipCode": "60707",
    "hospitalCity": "Chicago",
    "hospitalState": "Illinois",
    "hospitalId": None,
    "tempToHire": False,
    "hospitalLocation": [
        "Chicago, Illinois",
        "IL",
        "Illinois",
        "Chicago, Illinois"
    ],
    "hospitalWebsite": "",
    "showHospital": True,
    "agencyId": 133,
    "agency": {
        "id": 133,
        "name": "Supplemental Health Care",
        "description": "",
        "photoFilename": "supplemental-health-care-logo-1628278211990.png",
        "organization": {
            "id": 263
        },
        "employerType": "agency",
        "recruiterIds": [
            579942
        ]
    },
    "agencyPhoto": "supplemental-health-care-logo-1628278211990.png",
    "location": [
        "Chicago, Illinois",
        "IL",
        "Illinois",
        "Chicago, Illinois"
    ],
    "discipline": "RN",
    "disciplineId": 1,
    "nurseflyDiscipline": "RN",
    "specialty": [
        "Med Surg"
    ],
    "specialtyIds": [
        22
    ],
    "nurseflySpecialty": [
        "Med Surg"
    ],
    "startDate": 1643673600,
    "shiftDetails": "12 hours, nights",
    "contractLength": 7,
    "hoursPerDay": 12,
    "hoursPerWeek": "36.00",
    "maxHoursPerWeek": "0.00",
    "insuranceProvider": None,
    "insuranceCompanyName": None,
    "housingOption": None,
    "housingApartment": None,
    "housingHotel": None,
    "cityData": {
        "id": 17,
        "city_state": "chicago, il",
        "city_image": "chicagoil.jpg",
        "latitude": 41.83755,
        "longitude": -87.68184,
        "livability_score": "60",
        "name": "Chicago",
        "state": "Illinois",
        "zip": "60707"
    },
    "cityDataId": 17,
    "nights": True,
    "days": False,
    "evenings": False,
    "flexible": False,
    "message": "M/S nurses provide care and treatment to ill, injured, and recovering adults.",
    "searchTitle": "Travel RN - Med Surg",
    "searchDescription": "Chicago IL M/S nurses provide care and treatment to ill, injured, and recovering adults.",
    "perks": "Med Surg - 7 week contract- Must have general surgical experience",
    "autoposted": True,
    "startMonth": [
        "Feb 2022",
        "ASAP"
    ],
    "shiftFilter": [
        "Nights"
    ],
    "contractLengthWeeks": "7 weeks",
    "createdAt": 1642779531,
    "setting": None,
    "employmentType": "Travel",
    "campaigns": [],
    "hidden": True,
    "hourlyPay": 110,
    "weeklyPay": 3928,
    "weeklyTaxablePay": 2304,
    "weeklyNonTaxablePay": 1624,
    "pay": {
        "minRate": 3928,
        "maxRate": 3928,
        "period": "week",
        "display": {
            "disclaimer": "Estimated pay package",
            "full": "$3,928/week",
            "short": "$3,928/wk",
            "per": "$3,928 per week",
            "rateOnly": "$3,928",
            "shortMax": "$3,928/wk",
            "period": "week",
            "periodShort": "wk",
            "periodAdverb": "weekly"
        }
    },
    "housingStipend": 1624,
    "mealStipend": 0,
    "normalizedPay": 3928,
    "recruiterFullName": "Morgan Miller",
    "postedBy": 579942,
    "hiddenPostedBy": 579942,
    "source": "manual",
    "additionalData": {},
    "percentageBudgetUsed": 0,
    "overtimePolicy": "After 40",
    "overtimePolicyDisplay": "OT after 40 hours",
    "gating": {
        "RESUME_REQUIRED": False
    },
    "_geoloc": {
        "lat": 41.83755,
        "lng": -87.68184
    },
    "recruiterIds": [
        579942
    ],
    "verbiage": {
        "seeking": "travel nurse RN Med Surg for a travel nursing job",
        "titles": {
            "simple": "Med Surg (RN)",
            "verbose": "Travel Nurse RN - Med Surg"
        }
    },
    "objectID": "jp-5534141"
})

algolia_query_example = json.dumps({
    "args": "permanent RN",
    "kwargs": {
        "filters": "(location:'New Orleans' OR location:'San Francisco' OR location:'New York' OR location:'Chicago' OR location:'Austin') AND employmentType:Permanent AND pay.minRate >= 40 AND pay.period:hour",
        "advancedSyntax": True,
        "optionalWords": "permanent, RN, New Orleans, San Francisco, New York, Chicago, Austin"
    }
})
algolia_parameters_example = json.dumps({
    "locations": ["New Orleans", "San Francisco", "New York", "Chicago", "Austin"],
    "jobType": "permanent",
    "payMin": 15000,
    "payPeriod": "month",
    "specialty": "RN",
})

algolia_query_prompt = f"""
You are a code assistant that returns either Algolia search parameters for Python as JSON or "false".
Return "false" if the provided User Input is not suitable for an Algolia query.
Make this decision based on the provided Algolia JSON Object Shape.
Otherwise, return the *args and **kwargs that would be passed to the `index.search` Python function as JSON.
Always use the attribute name for each OR condition instead of using parentheses to wrap the OR conditions for a single attribute like `locations`.
If the `jobType` equals Permanent, then normalize the pay in the User Input using the `payMin` and `payPeriod` attributes to dollars per year, assuming 40 hours per week and 50 weeks per year.
If the `jobType` equals Travel, then normalize the pay in the User Input using the `payMin` and `payPeriod` attributes to dollars per week, assuming 40 hours per week.
Pick of the Job Type Options for the `jobType` value in the response.
Pick of the Pay Period Options for the `payPeriod` value in the response.
Example Algolia JSON Object Shape: {algolia_object_shape}.
Example User Input: {algolia_parameters_example}.
Example response: {algolia_query_example}
  - Job Type Options: Travel, Permanent, Local Contract, Per Diem/PRN, Locum Tenens
  - Pay Period Options: hour, week, year, visit
  - User Input: """

@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
def get_algolia_hits(completion, maxHits):
    args = completion['args']
    kwargs = completion['kwargs']
    kwargs["hitsPerPage"] = maxHits
    print('algolia search index args', args)
    print('algolia search index kwargs', kwargs)
    try:
        query_response = algolia_job_index.search(args, kwargs)
    except Exception as e:
        print('algolia index error', e)
        raise e
    return query_response

class PineconeDataStore(DataStore):
    def __init__(self):
        # Check if the index name is specified and exists in Pinecone
        if PINECONE_INDEX and PINECONE_INDEX not in pinecone.list_indexes():

            # Get all fields in the metadata object in a list
            fields_to_index = list(DocumentChunkMetadata.__fields__.keys())

            # Create a new index with the specified name, dimension, and metadata configuration
            try:
                print(
                    f"Creating index {PINECONE_INDEX} with metadata config {fields_to_index}"
                )
                pinecone.create_index(
                    PINECONE_INDEX,
                    dimension=1536,  # dimensionality of OpenAI ada v2 embeddings
                    metadata_config={"indexed": fields_to_index},
                )
                self.index = pinecone.Index(PINECONE_INDEX)
                print(f"Index {PINECONE_INDEX} created successfully")
            except Exception as e:
                print(f"Error creating index {PINECONE_INDEX}: {e}")
                raise e
        elif PINECONE_INDEX and PINECONE_INDEX in pinecone.list_indexes():
            # Connect to an existing index with the specified name
            try:
                print(f"Connecting to existing index {PINECONE_INDEX}")
                self.index = pinecone.Index(PINECONE_INDEX)
                print(f"Connected to index {PINECONE_INDEX} successfully")
            except Exception as e:
                print(f"Error connecting to index {PINECONE_INDEX}: {e}")
                raise e

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a dict from document id to list of document chunks and inserts them into the index.
        Return a list of document ids.
        """
        # Initialize a list of ids to return
        doc_ids: List[str] = []
        # Initialize a list of vectors to upsert
        vectors = []
        # Loop through the dict items
        for doc_id, chunk_list in chunks.items():
            # Append the id to the ids list
            for chunk in chunk_list:
                doc_id = chunk.id
                print(f"Upserting document_id: {doc_id}")
                # Create a vector tuple of (id, embedding, metadata)
                # Convert the metadata object to a dict with unix timestamps for dates
                pinecone_metadata = self._get_pinecone_metadata(chunk.metadata)
                # Add the text and document id to the metadata dict
                pinecone_metadata["text"] = chunk.text
                pinecone_metadata["document_id"] = doc_id
                vector = (chunk.id, chunk.embedding, pinecone_metadata)
                vectors.append(vector)

        # Split the vectors list into batches of the specified size
        batches = [
            vectors[i : i + UPSERT_BATCH_SIZE]
            for i in range(0, len(vectors), UPSERT_BATCH_SIZE)
        ]
        # Upsert each batch to Pinecone
        for batch in batches:
            try:
                print(f"Upserting batch of size {len(batch)}")
                self.index.upsert(vectors=batch)
                print(f"Upserted batch successfully")
            except Exception as e:
                print(f"Error upserting batch: {e}")
                raise e

        return doc_ids

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
    async def _query(
        self,
        queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """

        # Define a helper coroutine that performs a single query and returns a QueryResult
        async def _single_query(query: QueryWithEmbedding) -> QueryResult:
            print(f"Query: {query.query}, {query.filter}")
            is_algolia = False
            try:
                algolia_prompt_params = {
                    'jobType': query.filter.periodicity,
                    'locations': query.filter.locations,
                    'specialty': query.filter.specialty,
                    'payMin': query.filter.pay.min,
                    'payPeriod': query.filter.pay.period,
                }
                print('algolia prompt params', algolia_prompt_params)
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "system", "content": algolia_query_prompt + json.dumps(algolia_prompt_params) }],
                    temperature=0,
                )
                choices = response["choices"]
                completion = json.loads(choices[0].message.content.strip())
                print('algolia prompt completion', completion)

                if completion is False:
                    # Call Pinecone
                    # Query the index with the query embedding and top_k
                    query_response = self.index.query(
                        # namespace=namespace,
                        top_k=query.top_k,
                        vector=query.embedding,
                        include_metadata=True,
                    )
                else:
                    is_algolia = True
                    query_response = get_algolia_hits(completion, query.top_k)
            except Exception as e:
                print(f"Error querying index: {e}")
                raise e

            query_results: List[DocumentChunkWithScore] = []
            if not is_algolia:
                results = query_response.matches
            else:
                results = query_response['hits']
                print('got ', len(results), ' algolia hits')
            for result in results:
                id_ = ''
                if not is_algolia:
                    id_ = str(result.id)
                    score = result.score
                    metadata = result.metadata
                else:
                    del result["_highlightResult"]
                    id_ = str(result['objectID'])
                    score = 1
                    metadata = {
                        "text": json.dumps(result),
                        'document_id': id_,
                        'source': 'file',
                    }
                # Remove document id and text from metadata and store it in a new variable
                metadata_without_text = (
                    {key: value for key, value in metadata.items() if key != "text"}
                    if metadata
                    else None
                )

                # If the source is not a valid Source in the Source enum, set it to None
                if (
                    metadata_without_text
                    and "source" in metadata_without_text
                    and metadata_without_text["source"] not in Source.__members__
                ):
                    metadata_without_text["source"] = None

                # Create a document chunk with score object with the result data
                metadata_without_text['vivian_job_link'] = 'https://www.vivian.com/job/' + id_
                print('new result', id_)
                print('\tscore', score)
                print('\ttext', metadata["text"])
                print('\tmetadata_without_text', metadata_without_text)
                print()
                result = DocumentChunkWithScore(
                    id=id_,
                    score=score,
                    text=metadata["text"] if metadata and "text" in metadata else None,
                    metadata=metadata_without_text,
                )
                query_results.append(result)
            return QueryResult(query=query.query, results=query_results)

        # Use asyncio.gather to run multiple _single_query coroutines concurrently and collect their results
        results: List[QueryResult] = await asyncio.gather(
            *[_single_query(query) for query in queries]
        )

        return results

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes vectors by ids, filter, or everything from the index.
        """
        # Delete all vectors from the index if delete_all is True
        if delete_all:
            try:
                print(f"Deleting all vectors from index")
                self.index.delete(delete_all=True)
                print(f"Deleted all vectors successfully")
                return True
            except Exception as e:
                print(f"Error deleting all vectors: {e}")
                raise e

        # Convert the metadata filter object to a dict with pinecone filter expressions
        pinecone_filter = self._get_pinecone_filter(filter)
        # Delete vectors that match the filter from the index if the filter is not empty
        if pinecone_filter != {}:
            try:
                print(f"Deleting vectors with filter {pinecone_filter}")
                self.index.delete(filter=pinecone_filter)
                print(f"Deleted vectors with filter successfully")
            except Exception as e:
                print(f"Error deleting vectors with filter: {e}")
                raise e

        # Delete vectors that match the document ids from the index if the ids list is not empty
        if ids is not None and len(ids) > 0:
            try:
                print(f"Deleting vectors with ids {ids}")
                pinecone_filter = {"document_id": {"$in": ids}}
                self.index.delete(filter=pinecone_filter)  # type: ignore
                print(f"Deleted vectors with ids successfully")
            except Exception as e:
                print(f"Error deleting vectors with ids: {e}")
                raise e

        return True

    def _get_pinecone_filter(
        self, filter: Optional[DocumentMetadataFilter] = None
    ) -> Dict[str, Any]:
        if filter is None:
            return {}

        pinecone_filter = {}

        # For each field in the MetadataFilter, check if it has a value and add the corresponding pinecone filter expression
        # For start_date and end_date, uses the $gte and $lte operators respectively
        # For other fields, uses the $eq operator
        for field, value in filter.dict().items():
            if value is not None:
                if field == "start_date":
                    pinecone_filter["date"] = pinecone_filter.get("date", {})
                    pinecone_filter["date"]["$gte"] = to_unix_timestamp(value)
                elif field == "end_date":
                    pinecone_filter["date"] = pinecone_filter.get("date", {})
                    pinecone_filter["date"]["$lte"] = to_unix_timestamp(value)
                else:
                    pinecone_filter[field] = value

        return pinecone_filter

    def _get_pinecone_metadata(
        self, metadata: Optional[DocumentChunkMetadata] = None
    ) -> Dict[str, Any]:
        if metadata is None:
            return {}

        pinecone_metadata = {}

        # For each field in the Metadata, check if it has a value and add it to the pinecone metadata dict
        # For fields that are dates, convert them to unix timestamps
        for field, value in metadata.dict().items():
            if value is not None:
                if field in ["created_at"]:
                    pinecone_metadata[field] = to_unix_timestamp(value)
                else:
                    pinecone_metadata[field] = value

        return pinecone_metadata
