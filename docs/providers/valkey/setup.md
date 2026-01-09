# Valkey

[Valkey](https://valkey.io/) is an open-source, high-performance key-value datastore that supports a variety of workloads such as caching, message queues, and can act as a primary database. Valkey is a Redis fork that maintains API compatibility while providing enhanced performance and features. Use Valkey as a low-latency vector engine with the ValkeySearch module.

- The database **needs the Valkey Search module**, which provide vector search capabilities.
- Run the App with the Valkey docker image: `docker compose up -d` in [this dir](/examples/docker/valkey).
- The app automatically creates a Valkey vector search index on the first run. Optionally, create a custom index with a specific name and set it as an environment variable (see below).
- To enable more hybrid searching capabilities, adjust the document schema [here](/datastore/providers/valkey_datastore.py).

**Environment Variables:**

| Name                     | Required | Description                       | Default     |
| ------------------------ | -------- |-----------------------------------| ----------- |
| `DATASTORE`              | Yes      | Datastore name, set to `valkey`   |             |
| `BEARER_TOKEN`           | Yes      | Secret token                      |             |
| `OPENAI_API_KEY`         | Yes      | OpenAI API key                    |             |
| `VALKEY_HOST`            | Optional | Valkey host url                   | `localhost` |
| `VALKEY_PORT`            | Optional | Valkey port                       | `6379`      |
| `VALKEY_PASSWORD`        | Optional | Valkey password                   | none        |
| `VALKEY_INDEX_NAME`      | Optional | Valkey vector index name          | `index`     |
| `VALKEY_DOC_PREFIX`      | Optional | Valkey key prefix for the index   | `doc`       |
| `VALKEY_DISTANCE_METRIC` | Optional | Vector similarity distance metric | `COSINE`    |
| `VALKEY_INDEX_TYPE`      | Optional | Vector index type: FLAT or HNSW   | `FLAT`      |

## Valkey Datastore development & testing

In order to test your changes to the Valkey Datastore, you can run the following commands:

```bash
# Run Valkey with search capabilities
docker run -it --rm -p 6379:6379 valkey/valkey-bundle:latest
```
    
```bash
# Run the Valkey datastore tests
poetry run pytest -s ./tests/datastore/providers/valkey/test_valkey_datastore.py
```
