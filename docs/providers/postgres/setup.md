# Postgres

Postgres Database offers an easy and efficient way to store vectors via [pgvector](https://github.com/pgvector/pgvector) extension. To use pgvector, you will need to set up a PostgreSQL database with the pgvector extension enabled or use a managed solution that provides pgvector. For a hosted/managed solution, you can use any of the cloud vendors which support [pgvector](https://github.com/pgvector/pgvector#hosted-postgres).

- The database needs the `pgvector` extension.
- To initialize the database with the required tables for retreival plugin, you may use any tool you are more familiar with like [pgAdmin](https://www.pgadmin.org/), [DBeaver](https://dbeaver.io/), [DataGrip](https://www.jetbrains.com/datagrip/), or `psql` cli.

**Retrieval App Environment Variables**

| Name             | Required | Description                            |
| ---------------- | -------- | -------------------------------------- |
| `DATASTORE`      | Yes      | Datastore name. Set this to `postgres` |
| `BEARER_TOKEN`   | Yes      | Your secret token                      |
| `OPENAI_API_KEY` | Yes      | Your OpenAI API key                    |

**Postgres Datastore Environment Variables**

| Name          | Required | Description       | Default    |
| ------------- | -------- | ----------------- | ---------- |
| `PG_HOST`     | Optional | Postgres host     | localhost  |
| `PG_PORT`     | Optional | Postgres port     | `5432`     |
| `PG_PASSWORD` | Optional | Postgres password | `postgres` |
| `PG_USER`     | Optional | Postgres username | `postgres` |
| `PG_DB`       | Optional | Postgres database | `postgres` |

## Postgres Datastore local development & testing

In order to test your changes to the Postgres Datastore, you can follow the steps below:

1. Bring up a local database instance and install [`pgvector`](https://github.com/pgvector/pgvector#installation) extension. Note that the next steps assumes that you have a database and a user named postgres.

1. Run the initialization script to create the tables required for retrieval plugin:
```bash
psql -h localhost -p 5432 -U postgres -d postgres -f examples/providers/postgres/init.sql
```

3. Export environment variables required for the Postgres Datastore
```bash
export PG_HOST=localhost
export PG_PORT=5432
export PG_PASSWORD=mysecretpassword
```

4. Run the Postgres datastore tests from the project's root directory
```bash
# Run the Postgres datastore tests
# go to project's root directory and run
poetry run pytest -s ./tests/datastore/providers/postgres/test_postgres_datastore.py
```

> **Warning**: The above steps are only for test/development. Please follow the respective vendor's security best practises when going to prod.

## Indexes for Postgres

By default, pgvector performs exact nearest neighbor search. To speed up the vector comparison, you may want to create indexes for the `embedding` column in the `documents` table. You should do this **only** after a few thousand records are inserted.

As datastore is using inner product for similarity search, you can add index as follows:

```sql
create index on documents using ivfflat (embedding vector_ip_ops) with (lists = 100);
```

To choose `lists` constant - a good place to start is records / 1000 for up to 1M records and sqrt(records) for over 1M records

For more information about indexes, see [pgvector docs](https://github.com/pgvector/pgvector#indexing).
