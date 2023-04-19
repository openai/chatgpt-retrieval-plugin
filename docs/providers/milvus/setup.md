# Milvus

[Milvus](https://milvus.io/) is the open-source, cloud-native vector database that scales to billions of vectors. It's the open-source version of Zilliz. It supports:

- Various indexing algorithms and distance metrics
- Scalar filtering and time travel searches
- Rollback and snapshots
- Multi-language SDKs
- Storage and compute separation
- Cloud scalability
- A developer-first community with multi-language support

Visit the [Github](https://github.com/milvus-io/milvus) to learn more.

## Deploying the Database

You can deploy and manage Milvus using Docker Compose, Helm, K8's Operator, or Ansible. Follow the instructions [here](https://milvus.io/docs) to get started.

**Environment Variables:**

| Name                       | Required | Description                                                                                                                                  |
|----------------------------| -------- |----------------------------------------------------------------------------------------------------------------------------------------------|
| `DATASTORE`                | Yes      | Datastore name, set to `milvus`                                                                                                              |
| `BEARER_TOKEN`             | Yes      | Your bearer token                                                                                                                            |
| `OPENAI_API_KEY`           | Yes      | Your OpenAI API key                                                                                                                          |
| `MILVUS_COLLECTION`        | Optional | Milvus collection name, defaults to a random UUID                                                                                            |
| `MILVUS_HOST`              | Optional | Milvus host IP, defaults to `localhost`                                                                                                      |
| `MILVUS_PORT`              | Optional | Milvus port, defaults to `19530`                                                                                                             |
| `MILVUS_USER`              | Optional | Milvus username if RBAC is enabled, defaults to `None`                                                                                       |
| `MILVUS_PASSWORD`          | Optional | Milvus password if required, defaults to `None`                                                                                              |
| `MILVUS_INDEX_PARAMS`      | Optional | Custom index options for the collection, defaults to `{"metric_type": "IP", "index_type": "HNSW", "params": {"M": 8, "efConstruction": 64}}` |
| `MILVUS_SEARCH_PARAMS`     | Optional | Custom search options for the collection, defaults to `{"metric_type": "IP", "params": {"ef": 10}}`                                          |
| `MILVUS_CONSISTENCY_LEVEL` | Optional | Data consistency level for the collection, defaults to `Bounded`                                                                             |

## Running Milvus Integration Tests

A suite of integration tests is available to verify the Milvus integration. To run the tests, run the milvus docker compose found in the examples folder.

Then, launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/milvus/test_milvus_datastore.py
```
