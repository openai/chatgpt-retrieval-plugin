
# LlamaIndex

[LlamaIndex](https://github.com/jerryjliu/llama_index) is a central interface to connect your LLM's with external data.
It provides a suite of in-memory indices over your unstructured and structured data for use with ChatGPT.
Unlike standard vector databases, LlamaIndex supports a wide range of indexing strategies (e.g. tree, keyword table, knowledge graph) optimized for different use-cases.
It is light-weight, easy-to-use, and requires no additional deployment.
All you need to do is specifying a few environment variables (optionally point to an existing saved Index json file).
Note that metadata filters in queries are not yet supported.

## Setup
Currently, LlamaIndex requires no additional deployment
and runs as a part of the Retrieval Plugin.
It is super easy to setup and great for quick prototyping
with ChatGPT and your external data.

**Retrieval App Environment Variables**

| Name             | Required | Description                         |
|------------------|----------|-------------------------------------|
| `DATASTORE`      | Yes      | Datastore name. Set this to `llama` |
| `BEARER_TOKEN`   | Yes      | Your secret token                   |
| `OPENAI_API_KEY` | Yes      | Your OpenAI API key                 |

**Llama Datastore Environment Variables**

| Name                           | Required | Description                          | Default       |
|--------------------------------|----------|--------------------------------------|---------------|
| `LLAMA_INDEX_TYPE`             | Optional | Index type (see below for details)   | `simple_dict` |
| `LLAMA_INDEX_JSON_PATH`        | Optional | Path to saved Index json file        | None          |
| `LLAMA_QUERY_KWARGS_JSON_PATH` | Optional | Path to saved query kwargs json file | None          |
| `LLAMA_RESPONSE_MODE`          | Optional | Response mode for query              | `no_text`     | 


**Different Index Types**
By default, we use a `GPTSimpleVectorIndex` to store document chunks in memory, 
and retrieve top-k nodes by embedding similarity.
Different index types are optimized for different data and query use-cases.
See this guide on [How Each Index Works](https://gpt-index.readthedocs.io/en/latest/guides/primer/index_guide.html) to learn more.
You can configure the index type via the `LLAMA_INDEX_TYPE`, see [here](https://gpt-index.readthedocs.io/en/latest/reference/indices/composability_query.html#gpt_index.data_structs.struct_type.IndexStructType) for the full list of accepted index type identifiers.


Read more details on [readthedocs](https://gpt-index.readthedocs.io/en/latest/), 
and engage with the community on [discord](https://discord.com/invite/dGcwcsnxhU).

## Running Tests
You can launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/llama/test_llama_datastore.py
```