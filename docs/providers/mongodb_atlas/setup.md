# MongoDB Atlas

MongoDB Atlas is a fully-managed, cloud-based database service developed by the creators of MongoDB. It simplifies the deployment and management of MongoDB databases, offering a comprehensive solution for scalable and resilient applications. With features such as automated backups, security controls, and multi-cloud support, MongoDB Atlas provides a reliable and flexible platform for your database needs, start by the documentation [MongoDB](https://www.mongodb.com/docs/atlas/getting-started/) or signing up for a free trial of [MongoDB Cloud](https://www.mongodb.com/es/cloud/atlas/register).

Begin by manually creating a [Atlas Search Index](https://www.mongodb.com/docs/atlas/atlas-vector-search/create-index/) Following that, proceed to:

**Environment Variables:**

| Name                  | Required | Description                                                                                                          |
| --------------------- | -------- | -------------------------------------------------------------------------------------------------------------------- |
| `DATASTORE`           | Yes      | Datastore name, set this to `mongodb`                                                              |
| `BEARER_TOKEN`        | Yes      | Your secret token for authenticating requests to the API                                                             |
| `OPENAI_API_KEY`      | Yes      | Your OpenAI API key for generating embeddings with the `text-embedding-ada-002` model                                |
| `MONGODB_INDEX` | No      | Your chosen MongoDB index name. Default is `default`. |

**Connection Evironment Variables:**

To establish a connection to the MongoDB database and collection, you must define the following variables:

| Name                     | Required | Description                                                                                      |
| ------------------------ | -------- | ------------------------------------------------------------------------------------------------ |
| `MONGODB_URI`      | Yes      | Your MongoDB URL.        |
| `MONGODB_DATABASE` | Yes      | Your MongoDB Database.      |
| `MONGODB_COLLECTION` | Yes      | Your MongoDB Collection     |

## Running MongoDB Integration Tests

A suite of integration tests is available to verify the Mongodb integration. The test suite needs the enviroment variables descripted above.

Then, launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/mongodb_atlas/test_mongodb_datastore.py
```
