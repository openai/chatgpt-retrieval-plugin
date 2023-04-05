# Qdrant

[Qdrant](https://qdrant.tech/) is a vector database that can store documents and vector embeddings. It can run as a self-hosted version or a managed [Qdrant Cloud](https://cloud.qdrant.io/)
solution. The configuration is almost identical for both options, except for the API key that [Qdrant Cloud](https://cloud.qdrant.io/) provides.

**Environment Variables:**

| Name                | Required | Description                                                 | Default            |
| ------------------- | -------- | ----------------------------------------------------------- | ------------------ |
| `DATASTORE`         | Yes      | Datastore name, set to `qdrant`                             |                    |
| `BEARER_TOKEN`      | Yes      | Secret token                                                |                    |
| `OPENAI_API_KEY`    | Yes      | OpenAI API key                                              |                    |
| `QDRANT_URL`        | Yes      | Qdrant instance URL                                         | `http://localhost` |
| `QDRANT_PORT`       | Optional | TCP port for Qdrant HTTP communication                      | `6333`             |
| `QDRANT_GRPC_PORT`  | Optional | TCP port for Qdrant GRPC communication                      | `6334`             |
| `QDRANT_API_KEY`    | Optional | Qdrant API key for [Qdrant Cloud](https://cloud.qdrant.io/) |                    |
| `QDRANT_COLLECTION` | Optional | Qdrant collection name                                      | `document_chunks`  |

## Qdrant Cloud

For a hosted [Qdrant Cloud](https://cloud.qdrant.io/) version, provide the Qdrant instance
URL and the API key from the [Qdrant Cloud UI](https://cloud.qdrant.io/).

**Example:**

```bash
QDRANT_URL="https://YOUR-CLUSTER-URL.aws.cloud.qdrant.io"
QDRANT_API_KEY="<YOUR_QDRANT_CLOUD_CLUSTER_API_KEY>"
```

The other parameters are optional and can be changed if needed.

## Self-hosted Qdrant Instance

For a self-hosted version, use Docker containers or the official Helm chart for deployment. The only
required parameter is the `QDRANT_URL` that points to the Qdrant server URL.

**Example:**

```bash
QDRANT_URL="http://YOUR_HOST.example.com:6333"
```

The other parameters are optional and can be changed if needed.

## Running Qdrant Integration Tests

A suite of integration tests verifies the Qdrant integration. To run it, start a local Qdrant instance in a Docker container.

```bash
docker run -p "6333:6333" -p "6334:6334" qdrant/qdrant:v1.0.3
```

Then, launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/qdrant/test_qdrant_datastore.py
```
