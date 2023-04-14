# Supabase

[Supabase](https://supabase.com/blog/openai-embeddings-postgres-vector) offers an easy and efficient way to store vectors via [pgvector](https://github.com/pgvector/pgvector) extension for Postgres Database. [You can use Supabase CLI](https://github.com/supabase/cli) to set up a whole Supabase stack locally or in the cloud or you can also use docker-compose, k8s and other options available. For a hosted/managed solution, try [Supabase.com](https://supabase.com/) and unlock the full power of Postgres with built-in authentication, storage, auto APIs, and Realtime features. For detailed setup instructions, refer to [`/docs/providers/supabase/setup.md`](/docs/providers/supabase/setup.md). See more helpful examples of Supabase & pgvector as a vector database [here](https://github.com/supabase-community/nextjs-openai-doc-search).

- The database needs the `pgvector` extension, which is included in [Supabase distribution of Postgres](https://github.com/supabase/postgres).
- It is possible to provide a Postgres connection string and an app will add `documents` table, query Postgres function, and `pgvector` extension automatically.
- But it is recommended to separate the migration process from an app. And execute the migration script in a different pipeline by using SQL statements from `_init_db()` function in [Supabase datastore provider](/datastore/providers/supabase_datastore.py).

Environment Variables:

| Name                        | Required | Description                                  | Default    |
| --------------------------- | -------- | -------------------------------------------- | ---------- |
| `DATASTORE`                 | Yes      | Datastore name, set to `supabase`            |            |
| `BEARER_TOKEN`              | Yes      | Secret token                                 |            |
| `OPENAI_API_KEY`            | Yes      | OpenAI API key                               |            |
| `SUPABASE_URL`              | Yes      | Supabase Project URL                         |            |
| `SUPABASE_ANON_KEY`         | Yes      | Supabase Project API anon key                |            |
| `SUPABASE_SERVICE_ROLE_KEY` | Optional | Supabase Project API service key             |            |
| `INIT_DB`                   | Optional | Set to true if you want to run DB migrations | `False`    |
| `PG_HOST`                   | Optional | Postgres host                                | none       |
| `PG_PORT`                   | Optional | Postgres port                                | `5432`     |
| `PG_PASSWORD`               | Optional | Postgres password                            | `postgres` |
| `PG_USER`                   | Optional | Postgres username                            | `postgres` |
| `PG_DB`                     | Optional | Postgres database                            | `postgres` |

## Supabase Datastore local development & testing

In order to test your changes to the Supabase Datastore, you can run the following commands:

1. Install [Supabase CLI](https://github.com/supabase/cli) and [Docker](https://docs.docker.com/get-docker/)

2. Run the Supabase `start` command from `examples/providers` directory. Config for Supabase local setup is available in `examples/providers/supabase` directory with required migrations.

```bash
# Run the Supabase stack using cli in docker
# go to examples/providers and run supabase start
cd examples/providers
supabase start
```

2. Supabase `start` will download docker images and launch Supabase stack locally. You will see similar output:

```bash
Applying migration 20230414142107_init_pg_vector.sql...
Seeding data supabase/seed.sql...
Started supabase local development setup.

         API URL: http://localhost:54321
          DB URL: postgresql://postgres:postgres@localhost:54322/postgres
      Studio URL: http://localhost:54323
    Inbucket URL: http://localhost:54324
      JWT secret: super-secret-jwt-token-with-at-least-32-characters-long
        anon key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
service_role key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU
```

3. Export environment variables required for the Supabase Datastore

```bash
export SUPABASE_URL=http://localhost:54321
export SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
```

4. Run the Supabase datastore tests from the project's root directory

```bash
# Run the Supabase datastore tests
# go to project's root directory and run
poetry run pytest -s ./tests/datastore/providers/supabase/test_supabase_datastore.py
```
