# pgvector

pgvector is a PostgreSQL extension that provides fast vector similarity search. To use pgvector, you will need to set up a PostgreSQL database with the pgvector extension enabled or use a managed solution that provides pgvector.

For more information about pgvector, visit the [official repository](https://github.com/pgvector/pgvector).

- The app **doesn't** create an index on the vector column. This provides perfect recall through exact nearest neighbor search.
- One you have a high number of rows, you can choose to create an index and setup appropriate number of lists. Check the [indexing documentation](https://github.com/pgvector/pgvector/#indexing) for details.


- Run the App with the Redis docker image: `docker compose up -d` in [this dir](/examples/docker/redis/).
- The app automatically creates a Redis vector search index on the first run. Optionally, create a custom index with a specific name and set it as an environment variable (see below).
- To enable more hybrid searching capabilities, adjust the document schema [here](/datastore/providers/redis_datastore.py).

**Environment Variables:**

| Name                 | Required | Description                                                                                | Default     |
| -------------------- | -------- | ------------------------------------------------------------------------------------------ | ----------- |
| `DATASTORE`          | Yes      | Datastore name, set to `pgvector`                                                          |             |
| `BEARER_TOKEN`       | Yes      | Secret token                                                                               |             |
| `OPENAI_API_KEY`     | Yes      | OpenAI API key                                                                             |             |
| `PGVECTOR_URL`       | Yes      | PostgreSQL connection URL with the pgvector extension enabled                              |             |
| `PGVECTOR_SSL`       | Optional | Set the SSL mode to require if set to true                                                 |  true       |  
| `PGVECTOR_COLLECTION`| Optional | PostgreSQL table name to store the vector documents                                        | `documents` |

## Cloud

pgvector is available on some cloud providers, such as

- [Supabase](https://supabase.com/)
- [Neon](https://neon.tech/]
- [Crunchy Bridge](https://www.crunchydata.com/products/crunchy-bridge)
- [bit.io](https://bit.io/)

For an updated list check the [official documentation](https://github.com/pgvector/pgvector/#hosted-postgres).

## Self-hosted pgvector Instance

You can add run a locally or self hosted instance of PostgreSQL with pgvector enable using Docker.

```bash
docker pull ankane/pgvector
```

```bash
docker run --name pgvector -e POSTGRES_PASSWORD=mysecretpassword -d postgres
```

Check PostgreSQL [official docker image](https://github.com/docker-library/docs/blob/master/postgres/README.md) for more options.