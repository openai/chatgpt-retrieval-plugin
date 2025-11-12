# Azure Cosmos DB

[Azure Cosmos DB](https://azure.microsoft.com/en-us/products/cosmos-db/) Azure Cosmos DB is a fully managed NoSQL and relational database for modern app development. Using Azure Cosmos DB for MongoDB vCore, you can store vector embeddings in your documents and perform [vector similarity search](https://learn.microsoft.com/azure/cosmos-db/mongodb/vcore/vector-search) on a fully managed MongoDB-compatible database service.

Learn more about Azure Cosmos DB for MongoDB vCore [here](https://learn.microsoft.com/azure/cosmos-db/mongodb/vcore/). If you don't have an Azure account, you can start setting one up [here](https://azure.microsoft.com/).

## Environment variables

| Name                         | Required | Description                                                             | Default             |
| ---------------------------- | -------- |-------------------------------------------------------------------------| ------------------- |
| `DATASTORE`                  | Yes      | Datastore name, set to `azurecosmosdb`                                  |                     |
| `BEARER_TOKEN`               | Yes      | Secret token                                                            |                     |
| `OPENAI_API_KEY`             | Yes      | OpenAI API key                                                          |                     |
| `AZCOSMOS_API`               | Yes      | Name of the API you're connecting to. Currently supported `mongo-vcore` |                     |
| `AZCOSMOS_CONNSTR`           | Yes      | The connection string to your account.                                  |                     |
| `AZCOSMOS_DATABASE_NAME`     | Yes      | The database where the data is stored/queried                           |                     |
| `AZCOSMOS_CONTAINER_NAME`    | Yes      | The container where the data is stored/queried                          |                     |

## Indexing
On first insert, the datastore will create the collection and index if necessary on the field `embedding`. Currently hybrid search is not yet supported.
