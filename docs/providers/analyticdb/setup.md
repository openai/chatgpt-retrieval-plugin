# AnalyticDB

[AnalyticDB](https://www.alibabacloud.com/help/en/analyticdb-for-postgresql/latest/product-introduction-overview) is a distributed cloud-native vector database designed for storing documents and vector embeddings. It is a high-performance vector database that is fully compatible with PostgreSQL syntax, making it easy to use. Managed by Alibaba Cloud, AnalyticDB offers a powerful vector compute engine, processing billions of data vectors and providing a wide range of features, including indexing algorithms, structured and unstructured data capabilities, real-time updates, distance metrics, scalar filtering, and time travel searches. Additionally, it offers full OLAP database functionality and an SLA commitment for production use.

## Install Requirements

Run the following command to install the required packages, including the `psycopg2cffi` package:

```
poetry install --extras "postgresql"
```

If you encounter the `Error: pg_config executable not found.` issue, you need to install the PostgreSQL development package on your system. Follow the instructions for your specific Linux distribution:

1. Debian-based systems (e.g., Ubuntu):

```bash
sudo apt-get update
sudo apt-get install libpq-dev
```

2. RHEL-based systems (e.g., CentOS, Fedora):

```bash
sudo yum install postgresql-devel
```

3. Arch-based systems (e.g., Manjaro, Arch Linux):

```bash
sudo pacman -S postgresql-libs
```

4. macOS:

```bash
brew install postgresql
```

After installing the required package, try to install `psycopg2cffi` again. If the `pg_config` executable is still not found, add its location to your system's `PATH` variable. You can typically find the `pg_config` executable in the `bin` directory of your PostgreSQL installation, for example `/usr/pgsql-13/bin/pg_config`. To add it to your `PATH` variable, use the following command (replace the path with the correct one for your system):

```bash
export PATH=$PATH:/usr/pgsql-13/bin
```

Now, try installing `psycopg2cffi` again using Poetry.

**Environment Variables:**

| Name             | Required | Description                         | Default           |
| ---------------- | -------- | ----------------------------------- | ----------------- |
| `DATASTORE`      | Yes      | Datastore name, set to `analyticdb` |                   |
| `BEARER_TOKEN`   | Yes      | Secret token                        |                   |
| `OPENAI_API_KEY` | Yes      | OpenAI API key                      |                   |
| `PG_HOST`        | Yes      | AnalyticDB instance URL             | `localhost`       |
| `PG_USER`        | Yes      | Database user                       | `user`            |
| `PG_PASSWORD`    | Yes      | Database password                   | `password`        |
| `PG_PORT`        | Optional | Port for AnalyticDB communication   | `5432`            |
| `PG_DATABASE`    | Optional | Database name                       | `postgres`        |
| `PG_COLLECTION`  | Optional | AnalyticDB relation name            | `document_chunks` |

## AnalyticDB Cloud

For a hosted [AnalyticDB Cloud](https://cloud.qdrant.io/) version, provide the AnalyticDB instance URL:

**Example:**

```bash
PG_HOST="https://YOUR-CLUSTER-URL.gpdb.rds.aliyuncs.com"
PG_USER="YOUR-USER-NAME"
PG_PASSWORD="YOUR-PASSWORD"
```

The other parameters are optional and can be changed if needed.

## Running AnalyticDB Integration Tests

A suite of integration tests verifies the AnalyticDB integration. Launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/analyticdb/test_analyticdb_datastore.py
```
