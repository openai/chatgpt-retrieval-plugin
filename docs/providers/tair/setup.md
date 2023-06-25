# Tair 

[Tair](https://www.alibabacloud.com/help/en/tair/latest/tairvector) is a cloud native in-memory database service that is developed by Alibaba Cloud. Tair is compatible with open source Redis and provides a variety of data models and enterprise-class capabilities to support your real-time online scenarios. Tair offers a powerful vector extension, processing billions of data vectors and providing a wide range of features, including indexing algorithms, structured attrs and unstructured vector capabilities, real-time updates, distance metrics, scalar filtering. Additionally, Tair offers  SLA commitment for production use。

## Install Requirements

Run the following command to install the tair python client:

```bash
pip3 install tair
```

**Environment Variables:**

| Name                   | Required | Description                            | Default     |
|------------------------|----------|----------------------------------------|-------------|
| `DATASTORE`            | Yes      | Datastore name, set to `tair`          |             |
| `BEARER_TOKEN`         | Yes      | Secret token                           |             |
| `OPENAI_API_KEY`       | Yes      | OpenAI API key                         |             |
| `TAIR_HOST`            | Yes      | Tair host url                          | `localhost` |
| `TAIR_PORT`            | Yes      | Tair port                              | `6379`      |
| `TAIR_USERNAME`        | Yes      | Tair username                          |             |
| `TAIR_PASSWORD`        | Yes      | Tair password                          |             |
| `TAIR_INDEX_NAME`      | Optional | Tair vector index name                 | `index`     |
| `TAIR_INDEX_TYPE`      | Optional | Tair vector index algorithms           | `FLAT`      |
| `TAIR_DISTANCE_METRIC` | Optional | Tair vector similarity distance metric | `InnerProduct`        |


## Tair 

For a hosted [Tair Cloud](https://www.alibabacloud.com/help/en/tair/latest/step-1-create-a-tair-instance) version, provide the Tair instance URL:

**Example:**

```bash
TAIR_HOST="https://YOUR-TAIR-INSTANCE-URL.rds.aliyuncs.com"
TAIR_PORT="YOUR-TAIR-INSTANCE-PORT"
TAIR_USERNAME="YOUR-TAIR-INSTANCE-USER-NAME"
TAIR_PASSWORD="YOUR-TAIR-INSTANCE-PASSWORD"
```

The other parameters are optional and can be changed if needed.

## Running Tair Integration Tests

A suite of integration tests verifies the Tair integration. Launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/tair/test_tair_datastore.py
```
