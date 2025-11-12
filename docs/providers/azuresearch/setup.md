# Azure Cognitive Search

[Azure Cognitive Search](https://azure.microsoft.com/products/search/) is a complete retrieval cloud service that supports vector search, text search, and hybrid (vectors + text combined to yield the best of the two approaches). Azure Cognitive Search also offers an [optional L2 re-ranking step](https://learn.microsoft.com/azure/search/semantic-search-overview) to further improve results quality.

You can find the Azure Cognitive Search documentation [here](https://learn.microsoft.com/azure/search/search-what-is-azure-search). If you don't have an Azure account, you can start setting one up [here](https://azure.microsoft.com/).

## Signing up for vector search

Azure Cognitive Search supports searching using pure vectors, pure text, or hybrid mode where both are combined. For the vector-based cases, you'll need to sign up for vector search private preview. To sign up, please fill in this form: https://aka.ms/VectorSearchSignUp

## Environment variables

| Name                          | Required | Description                                                                                                                                                                        | Default               |
| ----------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| `DATASTORE`                   | Yes      | Datastore name, set to `azuresearch`                                                                                                                                               |                       |
| `BEARER_TOKEN`                | Yes      | Secret token                                                                                                                                                                       |                       |
| `OPENAI_API_KEY`              | Yes      | OpenAI API key                                                                                                                                                                     |                       |
| `AZURESEARCH_SERVICE`         | Yes      | Name of your search service                                                                                                                                                        |                       |
| `AZURESEARCH_INDEX`           | Yes      | Name of your search index                                                                                                                                                          |                       |
| `AZURESEARCH_API_KEY`         | No       | Your API key, if using key-based auth instead of Azure managed identity                                                                                                            | Uses managed identity |
| `AZURESEARCH_DISABLE_HYBRID`  | No       | Disable hybrid search and only use vector similarity                                                                                                                               | Use hybrid search     |
| `AZURESEARCH_SEMANTIC_CONFIG` | No       | Enable L2 re-ranking with this configuration name [see re-ranking below](#re-ranking)                                                                                              | L2 not enabled        |
| `AZURESEARCH_LANGUAGE`        | No       | If using L2 re-ranking, language for queries/documents (valid values [listed here](https://learn.microsoft.com/rest/api/searchservice/preview-api/search-documents#queryLanguage)) | `en-us`               |
| `AZURESEARCH_DIMENSIONS`      | No       | Vector size for embeddings                                                                                                                                                         | 256, or other         |

## Authentication Options

- API key: this is enabled by default; you can obtain the key in the Azure Portal or using the Azure CLI.
- Managed identity: If the plugin is running in Azure, you can enable managed identity for the host and give that identity access to the service, without having to manage keys (avoiding secret storage, rotation, etc.). More details [here](https://learn.microsoft.com/azure/search/search-security-rbac).

## Re-ranking

Azure Cognitive Search offers the option to enable a second (L2) ranking step after retrieval to further improve results quality. This only applies when using text or hybrid search. Since it has latency and cost implications, if you want to try this option you need to explicitly [enable "semantic search"](https://learn.microsoft.com/azure/search/semantic-search-overview#enable-semantic-search) in your Cognitive Search service, and [create a semantic search configuration](https://learn.microsoft.com/azure/search/semantic-how-to-query-request#2---create-a-semantic-configuration) for your index.

## Using existing search indexes

If an existing index has fields that align with what's needed by the retrieval plugin but just differ in names, you can map your fields to the plugin fields using the following environment variables:

| Plugin field name | Environment variable to override it |
| ----------------- | ----------------------------------- |
| id                | AZURESEARCH_FIELDS_ID               |
| text              | AZURESEARCH_FIELDS_TEXT             |
| embedding         | AZURESEARCH_FIELDS_EMBEDDING        |
| document_id       | AZURESEARCH_FIELDS_DOCUMENT_ID      |
| source            | AZURESEARCH_FIELDS_SOURCE           |
| source_id         | AZURESEARCH_FIELDS_SOURCE_ID        |
| url               | AZURESEARCH_FIELDS_URL              |
| created_at        | AZURESEARCH_FIELDS_CREATED_AT       |
| author            | AZURESEARCH_FIELDS_AUTHOR           |
