#%%
from models.models import Source
from services.openai import get_chat_completion
import json
from typing import Dict
import os
from loguru import logger

from models.models import DocumentMetadata
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

# class DocumentMetadata(BaseModel):
#     source: Optional[Source] = None
#     source_id: Optional[str] = None
#     url: Optional[str] = None
#     created_at: Optional[str] = None
#     author: Optional[str] = None

#%%
# schema = DocumentMetadata.schema_json(indent=2)
# print(schema)
# def schema_to_function(schema: Any):
#     # assert schema.__doc__, f"{schema.__name__} is missing a docstring."
#     return {
#         "name": schema.__name__,
#         "description": schema.__doc__.strip(),
#         "parameters": schema.schema(),
#     }
# import orjson
# print(orjson.dumps(schema_to_function(DocumentMetadata), option=orjson.OPT_INDENT_2).decode())
# #%%
def extract_metadata_from_document(text: str) -> Dict[str, str]:
    sources = Source.__members__.keys()
    sources_string = ", ".join(sources)
    # This prompt is just an example, change it to fit your use case
    messages = [
        {
            "role": "system",
            "content": f"""
            Given a document from a user, try to extract the following metadata:
            - source: string, one of {sources_string}
            - url: string or don't specify
            - created_at: string or don't specify
            - author: string or don't specify

            Respond with a JSON containing the extracted metadata in key value pairs. If you don't find a metadata field, don't specify it.
            """,
        },
        {"role": "user", "content": text},
    ]

    # NOTE: Azure Open AI requires deployment id
    # Read environment variable - if not set - not used
    completion = get_chat_completion(
        messages=messages,
        model="gpt-4",
        deployment_id=os.environ.get("OPENAI_METADATA_EXTRACTIONMODEL_DEPLOYMENTID")
    )  # TODO: change to your preferred model name

    logger.info(f"completion: {completion}")

    try:
        metadata = json.loads(completion)
    except:
        metadata = {}

    return metadata
