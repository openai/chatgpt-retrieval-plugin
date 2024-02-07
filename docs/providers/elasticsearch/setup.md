# Elasticsearch

Elasticsearch is a search engine based on the Lucene library. It provides a distributed, full-text and vector search engine with an HTTP web interface and schema-free JSON documents. To use Elasticsearch as your vector database, start by [installing Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/install-elasticsearch.html) or signing up for a free trial of [Elastic Cloud](https://www.elastic.co/cloud/).

The app will create an Elasticsearch index for you automatically when you run it for the first time. Just pick a name for your index and set it as an environment variable.

**Environment Variables:**

| Name                  | Required | Description                                                                                                          |
| --------------------- | -------- | -------------------------------------------------------------------------------------------------------------------- |
| `DATASTORE`           | Yes      | Datastore name, set this to `elasticsearch`                                                                          |
| `BEARER_TOKEN`        | Yes      | Your secret token for authenticating requests to the API                                                             |
| `OPENAI_API_KEY`      | Yes      | Your OpenAI API key for generating embeddings with the OpenAI embeddings model                                       |
| `ELASTICSEARCH_INDEX` | Yes      | Your chosen Elasticsearch index name. **Note:** Index name must consist of lower case alphanumeric characters or '-' |

**Connection Evironment Variables:**
Depending on your Elasticsearch setup, you may need to set one of the following environment variables to connect to your Elasticsearch instance. If you are using Elastic Cloud, you can connect via `ELASTICSEARCH_CLOUD_ID`. If you are using a local instance of Elasticsearch, you will need to set `ELASTICSEARCH_URL`.

You can authenticate to Elasticsearch using either `ELASTICSEARCH_USERNAME` and `ELASTICSEARCH_PASSWORD` or `ELASTICSEARCH_API_KEY`. If you are using Elastic Cloud, you can find this in Kibana.

| Name                     | Required | Description                                                                                      |
| ------------------------ | -------- | ------------------------------------------------------------------------------------------------ |
| `ELASTICSEARCH_URL`      | Yes      | Your Elasticsearch URL. If installed locally, this would be https://localhost:9200               |
| `ELASTICSEARCH_CLOUD_ID` | Yes      | Your cloud id, linked to your deployment. This can be found in the deployment's console          |
| `ELASTICSEARCH_USERNAME` | Yes      | Your username for authenticating requests to the API. Commonly 'elastic'.                        |
| `ELASTICSEARCH_PASSWORD` | Yes      | Your password for authenticating requests to the API                                             |
| `ELASTICSEARCH_API_KEY`  | Yes      | Alternatively you can authenticate using api-key. This can be created in Kibana stack management |

## Running Elasticsearch Integration Tests

A suite of integration tests is available to verify the Elasticsearch integration. To run the tests, run the docker compose found in the `examples/docker/elasticsearch` folder with `docker-compose up`. This will start Elasticsearch in single node, security off mode, listening on `http://localhost:9200`.

Then, launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/elasticsearch/test_elasticsearch_datastore.py
```
