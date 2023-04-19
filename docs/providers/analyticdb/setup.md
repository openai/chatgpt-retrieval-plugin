# AnalyticDB

[AnalyticDB]( https://www.alibabacloud.com/help/en/analyticdb-for-postgresql/latest/product-introduction-overview) is a distributed cloud-native vector database designed for storing documents and vector embeddings. 
As a high-performance vector database, it is fully compatible with PostgreSQL syntax, making it easy to use. 
Managed by Alibaba Cloud, AnalyticDB is a cloud-native database with a powerful vector compute engine. 
Its out-of-the-box experience enables processing of billions of data vectors and offers a wide range of features, including indexing algorithms, structured and unstructured data capabilities, real-time updates, distance metrics, scalar filtering, and time travel searches. 
Additionally, it provides full OLAP database functionality and an SLA commitment for production use.

**Environment Variables:**

| Name             | Required | Description                         | Default           |
|------------------|----------|-------------------------------------|-------------------|
| `DATASTORE`      | Yes      | Datastore name, set to `analyticdb` |                   |
| `BEARER_TOKEN`   | Yes      | Secret token                        |                   |
| `OPENAI_API_KEY` | Yes      | OpenAI API key                      |                   |
| `PG_HOST`        | Yes      | AnalyticDB instance URL             | `localhost`       |
| `PG_USER`        | Yes      | Database user                       | `user`            |
| `PG_PASSWORD`    | Yes      | Database password                   | `password`        |
| `PG_PORT`        | Optional | Port for AnalyticDB communication   | `5432`            |
| `PG_DATABASE`    | Optional | Database name                       | `postgres`        |
| `PG_COLLECTION`  | Optional | AnalyticDB relation name            | `document_chunks` |

## AnalyticDB Cloud

For a hosted [AnalyticDB Cloud](https://cloud.qdrant.io/) version, provide the AnalyticDB instance
URL

**Example:**

```bash
PG_HOST="https://YOUR-CLUSTER-URL.gpdb.rds.aliyuncs.com"
PG_USER="YOUR-USER-NAME"
PG_PASSWORD="YOUR-PASSWORD"
```

The other parameters are optional and can be changed if needed.

## Running AnalyticDB Integration Tests

A suite of integration tests verifies the AnalyticDB integration. Launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/analyticdb/test_analyticdb_datastore.py
```