# Apache Cassandra

[Apache Cassandra®](https://docs.datastax.com/en/astra-serverless/docs/vector-search/overview.html) is a scalable, high-performance distributed database designed to handle large amounts of data for mission critical workloads. Cassandra powers ML/AI use cases in some of the largest compaines in the world including Uber, Apple, and Netflix. Get started using Cassandra [here](https://cassandra.apache.org/_/quickstart.html). For a db as a service solution from DataStax, check out [Astra DB](https://www.datastax.com/astra). For resources around using Cassandra for AI/ML see [awesome astra](https://awesome-astra.github.io/docs/pages/aiml/).

- Read about vector search in Cassandra in [this CEP](https://cwiki.apache.org/confluence/display/CASSANDRA/CEP-30%3A+Approximate+Nearest+Neighbor%28ANN%29+Vector+Search+via+Storage-Attached+Indexes)

**Environment Variables:**

| Name                    | Required | Description                                                                                                        | Default     |
|-------------------------| -------- |--------------------------------------------------------------------------------------------------------------------|-------------|
| `DATASTORE`             | Yes      | Datastore name, set to `cassandra`                                                                                 |             |
| `BEARER_TOKEN`          | Yes      | Secret token                                                                                                       |             |
| `OPENAI_API_KEY`        | Yes      | OpenAI API key                                                                                                     |             |
| `CASSANDRA_HOST`        | Optional | Contact points for Cassandra                                                                                       | `localhost` |
| `CASSANDRA_PORT`        | Optional | Cassandra port                                                                                                     | `9042`      |
| `CASSANDRA_USER`        | Optional | Cassandra user                                                                                                     | `cassandra` |
| `CASSANDRA_PASSWORD`    | Optional | Cassandra password                                                                                                 | `cassandra` |
| `CASSANDRA_KEYSPACE`    | Optional | Cassandra keyspace                                                                                                 | `cassandra` |
| `ASTRA_BUNDLE`          | Optional | Path to [Astra DB secure-connect bundle](https://docs.datastax.com/en/astra-serverless/docs/connect/secure-connect-bundle.html)                                                                              | None        |


## Cassandra Datastore development & testing
To run tests for the Cassandra Datastore run:

```bash
# Run the Redis datastore tests
poetry run pytest -s ./tests/datastore/providers/cassandra/test_cassandra_datastore.py
```