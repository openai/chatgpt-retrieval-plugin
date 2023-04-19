# Zilliz

[Zilliz](https://zilliz.com) is a managed cloud-native vector database designed for the billion scale. Zilliz offers many key features, such as:

- Multiple indexing algorithms
- Multiple distance metrics
- Scalar filtering
- Time travel searches
- Rollback and with snapshots
- Full RBAC
- 99.9% uptime
- Separated storage and compute
- Multi-language SDK's

Find more information [here](https://zilliz.com).

**Self Hosted vs SaaS**

Zilliz is a SaaS database, but offers an open-source solution, Milvus. Both options offer fast searches at the billion scale, but Zilliz handles data management for you. It automatically scales compute and storage resources and creates optimal indexes for your data. See the comparison [here](https://zilliz.com/doc/about_zilliz_cloud).

## Deploying the Database

Zilliz Cloud is deployable in a few simple steps. First, create an account [here](https://cloud.zilliz.com/signup). Once you have an account set up, follow the guide [here](https://zilliz.com/doc/quick_start) to set up a database and get the parameters needed for this application.

Environment Variables:

| Name                       | Required | Description                                                      |
|----------------------------| -------- |------------------------------------------------------------------|
| `DATASTORE`                | Yes      | Datastore name, set to `zilliz`                                  |
| `BEARER_TOKEN`             | Yes      | Your secret token                                                |
| `OPENAI_API_KEY`           | Yes      | Your OpenAI API key                                              |
| `ZILLIZ_COLLECTION`        | Optional | Zilliz collection name. Defaults to a random UUID                |
| `ZILLIZ_URI`               | Yes      | URI for the Zilliz instance                                      |
| `ZILLIZ_USER`              | Yes      | Zilliz username                                                  |
| `ZILLIZ_PASSWORD`          | Yes      | Zilliz password                                                  |
| `ZILLIZ_CONSISTENCY_LEVEL` | Optional | Data consistency level for the collection, defaults to `Bounded` |

## Running Zilliz Integration Tests

A suite of integration tests is available to verify the Zilliz integration. To run the tests, create a Zilliz database and update the environment variables.

Then, launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/zilliz/test_zilliz_datastore.py
```
