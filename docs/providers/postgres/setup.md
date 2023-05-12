# Postgres

Postgres Database offers an easy and efficient way to store vectors via [pgvector](https://github.com/pgvector/pgvector) extension. To use pgvector, you will need to set up a PostgreSQL database with the pgvector extension enabled or use a managed solution that provides pgvector. For a hosted/managed solution, you may try [Supabase](https://supabase.com/), more docs you can find in [Supabase Provider](/docs/providers/supabase/setup.md). See more helpful examples of Postgres & pgvector as a vector database [here](https://github.com/supabase-community/nextjs-openai-doc-search).

- The database needs the `pgvector` extension.
- To apply required migrations you may use any tool you are more familiar with like [pgAdmin](https://www.pgadmin.org/), [DBeaver](https://dbeaver.io/), [DataGrip](https://www.jetbrains.com/datagrip/), or `psql` cli.

**Retrieval App Environment Variables**

| Name             | Required | Description                            |
| ---------------- | -------- | -------------------------------------- |
| `DATASTORE`      | Yes      | Datastore name. Set this to `postgres` |
| `BEARER_TOKEN`   | Yes      | Your secret token                      |
| `OPENAI_API_KEY` | Yes      | Your OpenAI API key                    |

**Supabase Datastore Environment Variables**

| Name          | Required | Description       | Default    |
| ------------- | -------- | ----------------- | ---------- |
| `PG_HOST`     | Optional | Postgres host     | localhost  |
| `PG_PORT`     | Optional | Postgres port     | `5432`     |
| `PG_PASSWORD` | Optional | Postgres password | `postgres` |
| `PG_USER`     | Optional | Postgres username | `postgres` |
| `PG_DB`       | Optional | Postgres database | `postgres` |

## Postgres Datastore local development & testing

In order to test your changes to the Postgres Datastore, you can run the following:

1. You can run local or self-hosted instance of PostgreSQL with `pgvector` enabled using Docker.

```bash
docker pull ankane/pgvector
```

```bash
docker run --name pgvector -e POSTGRES_PASSWORD=mysecretpassword -d postgres
```

Check PostgreSQL [official docker image](https://github.com/docker-library/docs/blob/master/postgres/README.md) for more options.

2. Apply migrations using any tool you like most [pgAdmin](https://www.pgadmin.org/), [DBeaver](https://dbeaver.io/), [DataGrip](https://www.jetbrains.com/datagrip/), or `psql` cli.

```bash
# apply migrations using psql cli
psql -h localhost -p 5432 -U postgres -d postgres -f examples/providers/supabase/migrations/20230414142107_init_pg_vector.sql
```

3. Export environment variables required for the Postgres Datastore

```bash
export PG_HOST=localhost
export PG_PORT=54322
export PG_PASSWORD=mysecretpassword
```

4. Run the Postgres datastore tests from the project's root directory

```bash
# Run the Postgres datastore tests
# go to project's root directory and run
poetry run pytest -s ./tests/datastore/providers/postgres/test_postgres_datastore.py
```

5. When going to prod don't forget to set the password for the `postgres` user to something more secure and apply migrations.
