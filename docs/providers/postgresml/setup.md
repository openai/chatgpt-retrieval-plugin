# Postgres

PostgresML is a machine learning extension to Postgres that enables you to perform training and inference on text and tabular data using SQL queries. With PostgresML, you can enhance your existing DB using embeddings as well as perform additional NLP/traditional ML tasks.

## Free trial

If you want to check out the functionality quickly, [sign up for a free PostgresML account](https://postgresml.org/signup). We will provide 5GiB of storage for your data.

## Docker

Step 1: Clone this repository

```bash
git clone git@github.com:postgresml/postgresml.git
```

Step 2: Start dockerized services. PostgresML will run on port 5433, just in case you already have Postgres running. You can find Docker installation instructions [here](https://docs.docker.com/desktop/)

```bash
cd postgresml
docker-compose up
```

### Install `postgresql` command line utility

Ubuntu: `sudo apt install libpq-dev`

Centos/Fedora/Cygwin/Babun: `sudo yum install libpq-devel`

Mac: `brew install postgresql`

**Install `psycopg`**

`pip install psycopg`

**Retrieval App Environment Variables**

| Name             | Required | Description                            |
| ---------------- | -------- | -------------------------------------- |
| `DATASTORE`      | Yes      | Datastore name. Set this to `postgres` |
| `BEARER_TOKEN`   | Yes      | Your secret token                      |
| `OPENAI_API_KEY` | Yes      | Your OpenAI API key                    |

**Postgres Datastore Environment Variables**

| Name                        | Required | Description                                                        | Default            |
| ----------------------------| -------- | ------------------------------------------------------------------ | ------------------ |
| `PGML_HOST`                 | Optional | Hostname                                                           | `localhost`        |
| `PGML_PORT`                 | Optional | Port                                                               | `5433`             |
| `PGML_USERNAME`             | Optional | Username                                                           | `postgres`         |
| `PGML_PASSWORD`             | Optional | Password                                                           | ``                 | 
| `PGML_TABLENAME`            | Optional | Tablename                                                          | `chatgpt_datastore`| 
| `PGML_UPSERT_COMMAND`       | Optional | Command to upsert data - COPY or INSERT                            | `INSERT`           |