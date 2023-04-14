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
