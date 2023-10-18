# DashVector

[DashVector](https://help.aliyun.com/document_detail/2510225.html) is a fully-managed vectorDB service that supports high-dimension dense and sparse vectors , real-time insertion, and filtered search. It is built to scale automatically and can adapt to different application requirements. 

- To use DashVector as your vector database provider, you should create an API key in [DashVector console](https://dashvector.console.aliyun.com).
- The app will create a DashVector collection for you automatically when you run it for the first time. Just pick a name for your collection and set it as an environment variable.

**Environment Variables:**

| Name                    | Required | Description                                                                                                            |
|-------------------------| -------- | ---------------------------------------------------------------------------------------------------------------------- |
| `DATASTORE`             | Yes      | Datastore name, set this to `dashvector`                                                                               |
| `BEARER_TOKEN`          | Yes      | Your secret token for authenticating requests to the API                                                               |
| `OPENAI_API_KEY`        | Yes      | Your OpenAI API key for generating embeddings with the `text-embedding-ada-002` model                                  |
| `DASHVECTOR_API_KEY`    | Yes      | Your DashVector API key, found in the [DashVector console](https://dashvector.console.aliyun.com/)                     |
| `DASHVECTOR_COLLECTION` | Yes      | Your chosen DashVector collection name. **Note:** Collection name can only contains alphanumeric characters, `_` or `-`|

## Running DashVector Integration Tests

A suite of integration tests verifies the DashVector integration. Launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/dashvector/test_dashvector_datastore.py
```