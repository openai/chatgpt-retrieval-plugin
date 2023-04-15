#!/bin/sh
export DATASTORE=llama
export BEARER_TOKEN=1234567
export OPENAI_API_KEY=<YOUR OPENAI KEY HERE>

LLAMA_INDEX_TYPE=simple_dict
# LLAMA_INDEX_JSON_PATH=	Optional	Path to saved Index json file	None
# LLAMA_QUERY_KWARGS_JSON_PATH=	Optional	Path to saved query kwargs json file	None
LLAMA_RESPONSE_MODE=no_text