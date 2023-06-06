# Hologres

[Hologres](https://www.alibabacloud.com/help/en/hologres/latest/introduction) is a real-time interactive analytics engine that is compatible with PostgreSQL. Hologres seamlessly integrates with the big data ecosystem and supports queries of trillions of data records with high concurrency and low latency. Hologres also allows you to use Business Intelligence (BI) tools to analyze business data with ease.

Hologres provides high performance vector storage and nearest neighbour searching by deeply integrating `Proxima` index.
[Proxima](https://www.alibabacloud.com/help/en/hologres/latest/vector-processing) is a high-performance software library developed by Alibaba DAMO Academy. It allows you to search for the nearest neighbors of vectors. Proxima provides higher stability and performance than similar open source software such as Facebook AI Similarity Search (Faiss). Proxima provides basic modules that have leading performance and effects in the industry and allows you to search for similar text, images, videos, or human faces.

Click [here](https://www.alibabacloud.com/en/product/hologres) to fast deploy a Hologres cloud instance.

## Install Requirements

No extra packages needs to be installed. We use `psycopg2` to connect with Hologres since it is compatible with PostgreSQL protocol.

**Retrieval App Environment Variables**

| Name             | Required | Description                       |
| ---------------- | -------- | --------------------------------- |
| `DATASTORE`      | Yes      | Datastore name, set to `hologres` |
| `BEARER_TOKEN`   | Yes      | Your secret token                 |
| `OPENAI_API_KEY` | Yes      | Your OpenAI API key               |

**Hologres Datastore Environment Variables**

| Name          | Required | Description            | Default           |
| ------------- | -------- | ---------------------- | ----------------- |
| `PGHOST`      | Yes      | Hologres instance URL  |                   |
| `PGUSER`      | Yes      | Database user          |                   |
| `PGPASSWORD`  | Yes      | Database password      |                   |
| `PGPORT`      | Optional | Hologres instance port | `80`              |
| `PGDATABASE`  | Optional | Database name          | `postgres`        |
| `PGTABLENAME` | Optional | Table to store data    | `document_chunks` |

## Hologres Cloud

Provide the instance connection info in the environment variables.
Find the host url in the instance details page of the [console](https://hologram.console.aliyun.com).

**Example:**

```bash
PGHOST="hgprecn-cn-xxxxxxxxx-xx-xxxxxxxx.hologres.aliyuncs.com"
PGUSER="BASIC\$user"
PGPASSWORD="YOUR-PASSWORD"
```

The other parameters are optional and can be changed if needed.

## Running Hologres Integration Tests

A suite of integration tests verifies the Hologres integration. Launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/hologres/test_hologres_datastore.py
```
