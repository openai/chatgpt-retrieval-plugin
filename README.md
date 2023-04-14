# ChatGPT Retrieval Plugin

> **Join the [ChatGPT plugins waitlist here](https://openai.com/waitlist/plugins)!**

Find an example video of a Retrieval Plugin that has access to the UN Annual Reports from 2018 to 2022 [here](https://cdn.openai.com/chat-plugins/retrieval-gh-repo-readme/Retrieval-Final.mp4).

## Introduction

The ChatGPT Retrieval Plugin repository provides a flexible solution for semantic search and retrieval of personal or organizational documents using natural language queries. The repository is organized into several directories:

| Directory                     | Description                                                                                                                |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| [`datastore`](/datastore)     | Contains the core logic for storing and querying document embeddings using various vector database providers.              |
| [`docs`](/docs)               | Includes documentation for setting up and using each vector database provider, webhooks, and removing unused dependencies. |
| [`examples`](/examples)       | Provides example configurations, authentication methods, and provider-specific examples.                                   |
| [`models`](/models)           | Contains the data models used by the plugin, such as document and metadata models.                                         |
| [`scripts`](/scripts)         | Offers scripts for processing and uploading documents from different data sources.                                         |
| [`server`](/server)           | Houses the main FastAPI server implementation.                                                                             |
| [`services`](/services)       | Contains utility services for tasks like chunking, metadata extraction, and PII detection.                                 |
| [`tests`](/tests)             | Includes integration tests for various vector database providers.                                                          |
| [`.well-known`](/.well-known) | Stores the plugin manifest file and OpenAPI schema, which define the plugin configuration and API specification.           |

This README provides detailed information on how to set up, develop, and deploy the ChatGPT Retrieval Plugin.

## Table of Contents

- [Quickstart](#quickstart)
- [About](#about)
  - [Plugins](#plugins)
  - [Retrieval Plugin](#retrieval-plugin)
  - [Memory Feature](#memory-feature)
  - [Security](#security)
  - [API Endpoints](#api-endpoints)
- [Development](#development)
  - [Setup](#setup)
    - [General Environment Variables](#general-environment-variables)
  - [Choosing a Vector Database](#choosing-a-vector-database)
    - [Pinecone](#pinecone)
    - [Weaviate](#weaviate)
    - [Zilliz](#zilliz)
    - [Milvus](#milvus)
    - [Qdrant](#qdrant)
    - [Redis](#redis)
  - [Running the API Locally](#running-the-api-locally)
  - [Testing a Localhost Plugin in ChatGPT](#testing-a-localhost-plugin-in-chatgpt)
  - [Personalization](#personalization)
  - [Authentication Methods](#authentication-methods)
- [Deployment](#deployment)
- [Installing a Developer Plugin](#installing-a-developer-plugin)
- [Webhooks](#webhooks)
- [Scripts](#scripts)
- [Limitations](#limitations)
- [Contributors](#contributors)
- [Future Directions](#future-directions)

## Quickstart

Follow these steps to quickly set up and run the ChatGPT Retrieval Plugin:

1. Install Python 3.10, if not already installed.
2. Clone the repository: `git clone https://github.com/openai/chatgpt-retrieval-plugin.git`
3. Navigate to the cloned repository directory: `cd /path/to/chatgpt-retrieval-plugin`
4. Install poetry: `pip install poetry`
5. Create a new virtual environment with Python 3.10: `poetry env use python3.10`
6. Activate the virtual environment: `poetry shell`
7. Install app dependencies: `poetry install`
8. Set the required environment variables:

   ```
   export DATASTORE=<your_datastore>
   export BEARER_TOKEN=<your_bearer_token>
   export OPENAI_API_KEY=<your_openai_api_key>

   # Add the environment variables for your chosen vector DB.
   # Some of these are optional; read the provider's setup docs in /docs/providers for more information.

   # Pinecone
   export PINECONE_API_KEY=<your_pinecone_api_key>
   export PINECONE_ENVIRONMENT=<your_pinecone_environment>
   export PINECONE_INDEX=<your_pinecone_index>

   # Weaviate
   export WEAVIATE_HOST=<your_weaviate_host>
   export WEAVIATE_PORT=<your_weaviate_port>
   export WEAVIATE_INDEX=<your_weaviate_index>
   export WEAVIATE_USERNAME=<your_weaviate_username>
   export WEAVIATE_PASSWORD=<your_weaviate_password>
   export WEAVIATE_SCOPES=<your_weaviate_scopes>
   export WEAVIATE_BATCH_SIZE=<your_weaviate_batch_size>
   export WEAVIATE_BATCH_DYNAMIC=<your_weaviate_batch_dynamic>
   export WEAVIATE_BATCH_TIMEOUT_RETRIES=<your_weaviate_batch_timeout_retries>
   export WEAVIATE_BATCH_NUM_WORKERS=<your_weaviate_batch_num_workers>

   # Zilliz
   export ZILLIZ_COLLECTION=<your_zilliz_collection>
   export ZILLIZ_URI=<your_zilliz_uri>
   export ZILLIZ_USER=<your_zilliz_username>
   export ZILLIZ_PASSWORD=<your_zilliz_password>

   # Milvus
   export MILVUS_COLLECTION=<your_milvus_collection>
   export MILVUS_HOST=<your_milvus_host>
   export MILVUS_PORT=<your_milvus_port>
   export MILVUS_USER=<your_milvus_username>
   export MILVUS_PASSWORD=<your_milvus_password>

   # Qdrant
   export QDRANT_URL=<your_qdrant_url>
   export QDRANT_PORT=<your_qdrant_port>
   export QDRANT_GRPC_PORT=<your_qdrant_grpc_port>
   export QDRANT_API_KEY=<your_qdrant_api_key>
   export QDRANT_COLLECTION=<your_qdrant_collection>

   # Redis
   export REDIS_HOST=<your_redis_host>
   export REDIS_PORT=<your_redis_port>
   export REDIS_PASSWORD=<your_redis_password>
   export REDIS_INDEX_NAME=<your_redis_index_name>
   export REDIS_DOC_PREFIX=<your_redis_doc_prefix>
   export REDIS_DISTANCE_METRIC=<your_redis_distance_metric>
   export REDIS_INDEX_TYPE=<your_redis_index_type>
   ```

9. Run the API locally: `poetry run start`
10. Access the API documentation at `http://0.0.0.0:8000/docs` and test the API endpoints (make sure to add your bearer token).

### Testing in ChatGPT

To test a locally hosted plugin in ChatGPT, follow these steps:

1. Run the API on localhost: `poetry run dev`
2. Follow the instructions in the [Testing a Localhost Plugin in ChatGPT](#testing-a-localhost-plugin-in-chatgpt) section of the README.

For more detailed information on setting up, developing, and deploying the ChatGPT Retrieval Plugin, refer to the full Development section below.

## About

### Plugins

Plugins are chat extensions designed specifically for language models like ChatGPT, enabling them to access up-to-date information, run computations, or interact with third-party services in response to a user's request. They unlock a wide range of potential use cases and enhance the capabilities of language models.

Developers can create a plugin by exposing an API through their website and providing a standardized manifest file that describes the API. ChatGPT consumes these files and allows the AI models to make calls to the API defined by the developer.

A plugin consists of:

- An API
- An API schema (OpenAPI JSON or YAML format)
- A manifest (JSON file) that defines relevant metadata for the plugin

The Retrieval Plugin already contains all of these components. Read the Chat Plugins blogpost [here](https://openai.com/blog/chatgpt-plugins), and find the docs [here](https://platform.openai.com/docs/plugins/introduction).

### Retrieval Plugin

This is a plugin for ChatGPT that enables semantic search and retrieval of personal or organizational documents. It allows users to obtain the most relevant document snippets from their data sources, such as files, notes, or emails, by asking questions or expressing needs in natural language. Enterprises can make their internal documents available to their employees through ChatGPT using this plugin.

The plugin uses OpenAI's `text-embedding-ada-002` embeddings model to generate embeddings of document chunks, and then stores and queries them using a vector database on the backend. As an open-source and self-hosted solution, developers can deploy their own Retrieval Plugin and register it with ChatGPT. The Retrieval Plugin supports several vector database providers, allowing developers to choose their preferred one from a list.

A FastAPI server exposes the plugin's endpoints for upserting, querying, and deleting documents. Users can refine their search results by using metadata filters by source, date, author, or other criteria. The plugin can be hosted on any cloud platform that supports Docker containers, such as Fly.io, Heroku or Azure Container Apps. To keep the vector database updated with the latest documents, the plugin can process and store documents from various data sources continuously, using incoming webhooks to the upsert and delete endpoints. Tools like [Zapier](https://zapier.com) or [Make](https://www.make.com) can help configure the webhooks based on events or schedules.

### Memory Feature

A notable feature of the Retrieval Plugin is its capacity to provide ChatGPT with memory. By utilizing the plugin's upsert endpoint, ChatGPT can save snippets from the conversation to the vector database for later reference (only when prompted to do so by the user). This functionality contributes to a more context-aware chat experience by allowing ChatGPT to remember and retrieve information from previous conversations. Learn how to configure the Retrieval Plugin with memory [here](/examples/memory).

### Security

The Retrieval Plugin allows ChatGPT to search a vector database of content, and then add the best results into the ChatGPT session. This means it doesn’t have any external effects, and the main risk consideration is data authorization and privacy. Developers should only add content into their Retrieval Plugin that they have authorization for and that they are fine with appearing in users’ ChatGPT sessions. You can choose from a number of different authentication methods to secure the plugin (more information [here](#authentication-methods)).

### API Endpoints

The Retrieval Plugin is built using FastAPI, a web framework for building APIs with Python. FastAPI allows for easy development, validation, and documentation of API endpoints. Find the FastAPI documentation [here](https://fastapi.tiangolo.com/).

One of the benefits of using FastAPI is the automatic generation of interactive API documentation with Swagger UI. When the API is running locally, Swagger UI at `<local_host_url i.e. http://0.0.0.0:8000>/docs` can be used to interact with the API endpoints, test their functionality, and view the expected request and response models.

The plugin exposes the following endpoints for upserting, querying, and deleting documents from the vector database. All requests and responses are in JSON format, and require a valid bearer token as an authorization header.

- `/upsert`: This endpoint allows uploading one or more documents and storing their text and metadata in the vector database. The documents are split into chunks of around 200 tokens, each with a unique ID. The endpoint expects a list of documents in the request body, each with a `text` field, and optional `id` and `metadata` fields. The `metadata` field can contain the following optional subfields: `source`, `source_id`, `url`, `created_at`, and `author`. The endpoint returns a list of the IDs of the inserted documents (an ID is generated if not initially provided).

- `/upsert-file`: This endpoint allows uploading a single file (PDF, TXT, DOCX, PPTX, or MD) and storing its text and metadata in the vector database. The file is converted to plain text and split into chunks of around 200 tokens, each with a unique ID. The endpoint returns a list containing the generated id of the inserted file.

- `/query`: This endpoint allows querying the vector database using one or more natural language queries and optional metadata filters. The endpoint expects a list of queries in the request body, each with a `query` and optional `filter` and `top_k` fields. The `filter` field should contain a subset of the following subfields: `source`, `source_id`, `document_id`, `url`, `created_at`, and `author`. The `top_k` field specifies how many results to return for a given query, and the default value is 3. The endpoint returns a list of objects that each contain a list of the most relevant document chunks for the given query, along with their text, metadata and similarity scores.

- `/delete`: This endpoint allows deleting one or more documents from the vector database using their IDs, a metadata filter, or a delete_all flag. The endpoint expects at least one of the following parameters in the request body: `ids`, `filter`, or `delete_all`. The `ids` parameter should be a list of document IDs to delete; all document chunks for the document with these IDS will be deleted. The `filter` parameter should contain a subset of the following subfields: `source`, `source_id`, `document_id`, `url`, `created_at`, and `author`. The `delete_all` parameter should be a boolean indicating whether to delete all documents from the vector database. The endpoint returns a boolean indicating whether the deletion was successful.

The detailed specifications and examples of the request and response models can be found by running the app locally and navigating to http://0.0.0.0:8000/openapi.json, or in the OpenAPI schema [here](/.well-known/openapi.yaml). Note that the OpenAPI schema only contains the `/query` endpoint, because that is the only function that ChatGPT needs to access. This way, ChatGPT can use the plugin only to retrieve relevant documents based on natural language queries or needs. However, if developers want to also give ChatGPT the ability to remember things for later, they can use the `/upsert` endpoint to save snippets from the conversation to the vector database. An example of a manifest and OpenAPI schema that gives ChatGPT access to the `/upsert` endpoint can be found [here](/examples/memory).

To include custom metadata fields, edit the `DocumentMetadata` and `DocumentMetadataFilter` data models [here](/models/models.py), and update the OpenAPI schema [here](/.well-known/openapi.yaml). You can update this easily by running the app locally, copying the JSON found at http://0.0.0.0:8000/sub/openapi.json, and converting it to YAML format with [Swagger Editor](https://editor.swagger.io/). Alternatively, you can replace the `openapi.yaml` file with an `openapi.json` file.

## Development

### Setup

This app uses Python 3.10, and [poetry](https://python-poetry.org/) for dependency management.

Install Python 3.10 on your machine if it isn't already installed. It can be downloaded from the official [Python website](https://www.python.org/downloads/) or with a package manager like `brew` or `apt`, depending on your system.

Clone the repository from GitHub:

```
git clone https://github.com/openai/chatgpt-retrieval-plugin.git
```

Navigate to the cloned repository directory:

```
cd /path/to/chatgpt-retrieval-plugin
```

Install poetry:

```
pip install poetry
```

Create a new virtual environment that uses Python 3.10:

```
poetry env use python3.10
poetry shell
```

Install app dependencies using poetry:

```
poetry install
```

**Note:** If adding dependencies in the `pyproject.toml`, make sure to run `poetry lock` and `poetry install`.

#### General Environment Variables

The API requires the following environment variables to work:

| Name             | Required | Description                                                                                                                                                                                |
| ---------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `DATASTORE`      | Yes      | This specifies the vector database provider you want to use to store and query embeddings. You can choose from `pinecone`, `weaviate`, `zilliz`, `milvus`, `qdrant`, or `redis`.           |
| `BEARER_TOKEN`   | Yes      | This is a secret token that you need to authenticate your requests to the API. You can generate one using any tool or method you prefer, such as [jwt.io](https://jwt.io/).                |
| `OPENAI_API_KEY` | Yes      | This is your OpenAI API key that you need to generate embeddings using the `text-embedding-ada-002` model. You can get an API key by creating an account on [OpenAI](https://openai.com/). |

### Choosing a Vector Database

The plugin supports several vector database providers, each with different features, performance, and pricing. Depending on which one you choose, you will need to use a different Dockerfile and set different environment variables. The following sections provide brief introductions to each vector database provider.

For more detailed instructions on setting up and using each vector database provider, please refer to the respective documentation in the `/docs/providers/<datastore_name>/setup.md` file ([folders here](/docs/providers)).

#### Pinecone

[Pinecone](https://www.pinecone.io) is a managed vector database designed for speed, scale, and rapid deployment to production. It supports hybrid search and is currently the only datastore to natively support SPLADE sparse vectors. For detailed setup instructions, refer to [`/docs/providers/pinecone/setup.md`](/docs/providers/pinecone/setup.md).

#### Weaviate

[Weaviate](https://weaviate.io/) is an open-source vector search engine built to scale seamlessly into billions of data objects. It supports hybrid search out-of-the-box, making it suitable for users who require efficient keyword searches. Weaviate can be self-hosted or managed, offering flexibility in deployment. For detailed setup instructions, refer to [`/docs/providers/weaviate/setup.md`](/docs/providers/weaviate/setup.md).

#### Zilliz

[Zilliz](https://zilliz.com) is a managed cloud-native vector database designed for billion-scale data. It offers a wide range of features, including multiple indexing algorithms, distance metrics, scalar filtering, time travel searches, rollback with snapshots, full RBAC, 99.9% uptime, separated storage and compute, and multi-language SDKs. For detailed setup instructions, refer to [`/docs/providers/zilliz/setup.md`](/docs/providers/zilliz/setup.md).

#### Milvus

[Milvus](https://milvus.io/) is an open-source, cloud-native vector database that scales to billions of vectors. It is the open-source version of Zilliz and shares many of its features, such as various indexing algorithms, distance metrics, scalar filtering, time travel searches, rollback with snapshots, multi-language SDKs, storage and compute separation, and cloud scalability. For detailed setup instructions, refer to [`/docs/providers/milvus/setup.md`](/docs/providers/milvus/setup.md).

#### Qdrant

[Qdrant](https://qdrant.tech/) is a vector database capable of storing documents and vector embeddings. It offers both self-hosted and managed [Qdrant Cloud](https://cloud.qdrant.io/) deployment options, providing flexibility for users with different requirements. For detailed setup instructions, refer to [`/docs/providers/qdrant/setup.md`](/docs/providers/qdrant/setup.md).

#### Redis

[Redis](https://redis.com/solutions/use-cases/vector-database/) is a real-time data platform suitable for a variety of use cases, including everyday applications and AI/ML workloads. It can be used as a low-latency vector engine by creating a Redis database with the [Redis Stack docker container](/examples/docker/redis/docker-compose.yml). For a hosted/managed solution, [Redis Cloud](https://app.redislabs.com/#/) is available. For detailed setup instructions, refer to [`/docs/providers/redis/setup.md`](/docs/providers/redis/setup.md).

#### LlamaIndex

[LlamaIndex](https://github.com/jerryjliu/llama_index) is a central interface to connect your LLM's with external data.
It provides a suite of in-memory indices over your unstructured and structured data for use with ChatGPT.
Unlike standard vector databases, LlamaIndex supports a wide range of indexing strategies (e.g. tree, keyword table, knowledge graph) optimized for different use-cases.
It is light-weight, easy-to-use, and requires no additional deployment.
All you need to do is specifying a few environment variables (optionally point to an existing saved Index json file).
Note that metadata filters in queries are not yet supported.
For detailed setup instructions, refer to [`/docs/providers/llama/setup.md`](/docs/providers/llama/setup.md).

### Running the API locally

To run the API locally, you first need to set the requisite environment variables with the `export` command:

```
export DATASTORE=<your_datastore>
export BEARER_TOKEN=<your_bearer_token>
export OPENAI_API_KEY=<your_openai_api_key>
<Add the environment variables for your chosen vector DB here>
```

Start the API with:

```
poetry run start
```

Append `docs` to the URL shown in the terminal and open it in a browser to access the API documentation and try out the endpoints (i.e. http://0.0.0.0:8000/docs). Make sure to enter your bearer token and test the API endpoints.

**Note:** If you add new dependencies to the pyproject.toml file, you need to run `poetry lock` and `poetry install` to update the lock file and install the new dependencies.

### Testing a Localhost Plugin in ChatGPT

To test a localhost plugin in ChatGPT, use the provided [`local-server/main.py`](/local-server/main.py) file, which is specifically configured for localhost testing with CORS settings, no authentication and routes for the manifest, OpenAPI schema and logo.

Follow these steps to test your localhost plugin:

1. Run the localhost server using the `poetry run dev` command. This starts the server at the default address (e.g. `localhost:3333`).

2. Visit [ChatGPT](https://chat.openai.com/), select "Plugins" from the model picker, click on the plugins picker, and click on "Plugin store" at the bottom of the list.

3. Choose "Develop your own plugin" and enter your localhost URL (e.g. `localhost:3333`) when prompted.

4. Your localhost plugin is now enabled for your ChatGPT session.

For more information, refer to the [OpenAI documentation](https://platform.openai.com/docs/plugins/getting-started/openapi-definition).

### Personalization

You can personalize the Retrieval Plugin for your own use case by doing the following:

- **Replace the logo**: Replace the image in [logo.png](/.well-known/logo.png) with your own logo.

- **Edit the data models**: Edit the `DocumentMetadata` and `DocumentMetadataFilter` data models in [models.py](/models/models.py) to add custom metadata fields. Update the OpenAPI schema in [openapi.yaml](/.well-known/openapi.yaml) accordingly. To update the OpenAPI schema more easily, you can run the app locally, then navigate to `http://0.0.0.0:8000/sub/openapi.json` and copy the contents of the webpage. Then go to [Swagger Editor](https://editor.swagger.io/) and paste in the JSON to convert it to a YAML format. You could also replace the [openapi.yaml](/.well-known/openapi.yaml) file with an openapi.json file in the [.well-known](/.well-known) folder.

- **Change the plugin name, description, and usage instructions**: Update the plugin name, user-facing description, and usage instructions for the model. You can either edit the descriptions in the [main.py](/server/main.py) file or update the [openapi.yaml](/.well-known/openapi.yaml) file. Follow the same instructions as in the previous step to update the OpenAPI schema.

- **Enable ChatGPT to save information from conversations**: See the instructions in the [memory example folder](/examples/memory).

### Authentication Methods

You can choose from four options for authenticating requests to your plugin:

1. **No Authentication**: Anyone can add your plugin and use its API without any credentials. This option is suitable if you are only exposing documents that are not sensitive or already public. It provides no security for your data. If using this method, copy the contents of this [main.py](/examples/authentication-methods/no-auth/main.py) into the [actual main.py file](/server/main.py). Example manifest [here](/examples/authentication-methods/no-auth/ai-plugin.json).

2. **HTTP Bearer**: You can use a secret token as a header to authorize requests to your plugin. There are two variants of this option:

   - **User Level** (default for this implementation): Each user who adds your plugin to ChatGPT must provide the bearer token when adding the plugin. You can generate and distribute these tokens using any tool or method you prefer, such as [jwt.io](https://jwt.io/). This method provides better security as each user has to enter the shared access token. If you require a unique access token for each user, you will need to implement this yourself in the [main.py](/server/main.py) file. Example manifest [here](/examples/authentication-methods/user-http/ai-plugin.json).

   - **Service Level**: Anyone can add your plugin and use its API without credentials, but you must add a bearer token when registering the plugin. When you install your plugin, you need to add your bearer token, and will then receive a token from ChatGPT that you must include in your hosted manifest file. Your token will be used by ChatGPT to authorize requests to your plugin on behalf of all users who add it. This method is more convenient for users, but it may be less secure as all users share the same token and do not need to add a token to install the plugin. Example manifest [here](/examples/authentication-methods/service-http/ai-plugin.json).

3. **OAuth**: Users must go through an OAuth flow to add your plugin. You can use an OAuth provider to authenticate users who add your plugin and grant them access to your API. This method offers the highest level of security and control, as users authenticate through a trusted third-party provider. However, you will need to implement the OAuth flow yourself in the [main.py](/server/main.py) file and provide the necessary parameters in your manifest file. Example manifest [here](/examples/authentication-methods/oauth/ai-plugin.json).

Consider the benefits and drawbacks of each authentication method before choosing the one that best suits your use case and security requirements. If you choose to use a method different to the default (User Level HTTP), make sure to update the manifest file [here](/.well-known/ai-plugin.json).

## Deployment

You can deploy your app to different cloud providers, depending on your preferences and requirements. However, regardless of the provider you choose, you will need to update two files in your app: [openapi.yaml](/.well-known/openapi.yaml) and [ai-plugin.json](/.well-known/ai-plugin.json). As outlined above, these files define the API specification and the AI plugin configuration for your app, respectively. You need to change the url field in both files to match the address of your deployed app.

Before deploying your app, you might want to remove unused dependencies from your [pyproject.toml](/pyproject.toml) file to reduce the size of your app and improve its performance. Depending on the vector database provider you choose, you can remove the packages that are not needed for your specific provider. Refer to the respective documentation in the [`/docs/deployment/removing-unused-dependencies.md`](/docs/deployment/removing-unused-dependencies.md) file for information on removing unused dependencies for each provider.

Once you have deployed your app, consider uploading an initial batch of documents using one of [these scripts](/scripts) or by calling the `/upsert` endpoint.

Here are detailed deployment instructions for various platforms:

- [Deploying to Fly.io](/docs/deployment/flyio.md)
- [Deploying to Heroku](/docs/deployment/heroku.md)
- [Other Deployment Options](/docs/deployment/other-options.md) (Azure Container Apps, Google Cloud Run, AWS Elastic Container Service, etc.)

After you create your app, make sure to change the plugin url in your plugin manifest file [here](/.well-known/ai-plugin.json), and in your OpenAPI schema [here](/.well-known/openapi.yaml), and redeploy.

## Installing a Developer Plugin

To install a developer plugin, follow the steps below:

- First, create your developer plugin by deploying it to your preferred hosting platform (e.g. Fly.io, Heroku, etc.) and updating the plugin URL in the manifest file and OpenAPI schema.

- Go to [ChatGPT](https://chat.openai.com/) and select "Plugins" from the model picker.

- From the plugins picker, scroll to the bottom and click on "Plugin store."

- Go to "Develop your own plugin" and follow the instructions provided. You will need to enter the domain where your plugin is deployed.

- Follow the instructions based on the authentication type you have chosen for your plugin (e.g. if your plugin uses Service Level HTTP, you will have to paste in your access token, then paste the new access token you receive from the plugin flow into your [ai-plugin.json](/.well-known/ai-plugin.json) file and redeploy your app).

- Next, you must add your plugin. Go to the "Plugin store" again and click on "Install an unverified plugin."

- Follow the instructions provided, which will require you to enter the domain where your plugin is deployed.

- Follow the instructions based on the authentication type you have chosen for your plugin (e.g. if your plugin uses User Level HTTP, you will have to paste in your bearer token).

After completing these steps, your developer plugin should be installed and ready to use in ChatGPT.

## Webhooks

To keep the documents stored in the vector database up-to-date, consider using tools like [Zapier](https://zapier.com) or [Make](https://www.make.com) to configure incoming webhooks to your plugin's API based on events or schedules. For example, this could allow you to sync new information as you update your notes or receive emails. You can also use a [Zapier Transfer](https://zapier.com/blog/zapier-transfer-guide/) to batch process a collection of existing documents and upload them to the vector database.

If you need to pass custom fields from these tools to your plugin, you might want to create an additional Retrieval Plugin API endpoint that calls the datastore's upsert function, such as `upsert-email`. This custom endpoint can be designed to accept specific fields from the webhook and process them accordingly.

To set up an incoming webhook, follow these general steps:

- Choose a webhook tool like Zapier or Make and create an account.
- Set up a new webhook or transfer in the tool, and configure it to trigger based on events or schedules.
- Specify the target URL for the webhook, which should be the API endpoint of your retrieval plugin (e.g. `https://your-plugin-url.com/upsert`).
- Configure the webhook payload to include the necessary data fields and format them according to your retrieval plugin's API requirements.
- Test the webhook to ensure it's working correctly and sending data to your retrieval plugin as expected.

After setting up the webhook, you may want to run a backfill to ensure that any previously missed data is included in the vector database.

Remember that if you want to use incoming webhooks to continuously sync data, you should consider running a backfill after setting these up to avoid missing any data.

In addition to using tools like Zapier and Make, you can also build your own custom integrations to sync data with your Retrieval Plugin. This allows you to have more control over the data flow and tailor the integration to your specific needs and requirements.

## Scripts

The `scripts` folder contains scripts to batch upsert or process text documents from different data sources, such as a zip file, JSON file, or JSONL file. These scripts use the plugin's upsert utility functions to upload the documents and their metadata to the vector database, after converting them to plain text and splitting them into chunks. Each script folder has a README file that explains how to use it and what parameters it requires. You can also optionally screen the documents for personally identifiable information (PII) using a language model and skip them if detected, with the [`services.pii_detection`](/services/pii_detection.py) module. This can be helpful if you want to avoid uploading sensitive or private documents to the vector database unintentionally. Additionally, you can optionally extract metadata from the document text using a language model, with the [`services.extract_metadata`](/services/extract_metadata.py) module. This can be useful if you want to enrich the document metadata. **Note:** if using incoming webhooks to continuously sync data, consider running a backfill after setting these up to avoid missing any data.

The scripts are:

- [`process_json`](scripts/process_json/): This script processes a file dump of documents in a JSON format and stores them in the vector database with some metadata. The format of the JSON file should be a list of JSON objects, where each object represents a document. The JSON object should have a `text` field and optionally other fields to populate the metadata. You can provide custom metadata as a JSON string and flags to screen for PII and extract metadata.
- [`process_jsonl`](scripts/process_jsonl/): This script processes a file dump of documents in a JSONL format and stores them in the vector database with some metadata. The format of the JSONL file should be a newline-delimited JSON file, where each line is a valid JSON object representing a document. The JSON object should have a `text` field and optionally other fields to populate the metadata. You can provide custom metadata as a JSON string and flags to screen for PII and extract metadata.
- [`process_zip`](scripts/process_zip/): This script processes a file dump of documents in a zip file and stores them in the vector database with some metadata. The format of the zip file should be a flat zip file folder of docx, pdf, txt, md, pptx or csv files. You can provide custom metadata as a JSON string and flags to screen for PII and extract metadata.

## Limitations

While the ChatGPT Retrieval Plugin is designed to provide a flexible solution for semantic search and retrieval, it does have some limitations:

- **Keyword search limitations**: The embeddings generated by the `text-embedding-ada-002` model may not always be effective at capturing exact keyword matches. As a result, the plugin might not return the most relevant results for queries that rely heavily on specific keywords. Some vector databases, like Pinecone and Weaviate, use hybrid search and might perform better for keyword searches.
- **Sensitive data handling**: The plugin does not automatically detect or filter sensitive data. It is the responsibility of the developers to ensure that they have the necessary authorization to include content in the Retrieval Plugin and that the content complies with data privacy requirements.
- **Scalability**: The performance of the plugin may vary depending on the chosen vector database provider and the size of the dataset. Some providers may offer better scalability and performance than others.
- **Language support**: The plugin currently uses OpenAI's `text-embedding-ada-002` model, which is optimized for use in English. However, it is still robust enough to generate good results for a variety of languages.
- **Metadata extraction**: The optional metadata extraction feature relies on a language model to extract information from the document text. This process may not always be accurate, and the quality of the extracted metadata may vary depending on the document content and structure.
- **PII detection**: The optional PII detection feature is not foolproof and may not catch all instances of personally identifiable information. Use this feature with caution and verify its effectiveness for your specific use case.

## Future Directions

The ChatGPT Retrieval Plugin provides a flexible solution for semantic search and retrieval, but there is always potential for further development. We encourage users to contribute to the project by submitting pull requests for new features or enhancements. Notable contributions may be acknowledged with OpenAI credits.

Some ideas for future directions include:

- **More vector database providers**: If you are interested in integrating another vector database provider with the ChatGPT Retrieval Plugin, feel free to submit an implementation.
- **Additional scripts**: Expanding the range of scripts available for processing and uploading documents from various data sources would make the plugin even more versatile.
- **User Interface**: Developing a user interface for managing documents and interacting with the plugin could improve the user experience.
- **Hybrid search / TF-IDF option**: Enhancing the [datastore's upsert function](/datastore/datastore.py#L18) with an option to use hybrid search or TF-IDF indexing could improve the plugin's performance for keyword-based queries.
- **Advanced chunking strategies and embeddings calculations**: Implementing more sophisticated chunking strategies and embeddings calculations, such as embedding document titles and summaries, performing weighted averaging of document chunks and summaries, or calculating the average embedding for a document, could lead to better search results.
- **Custom metadata**: Allowing users to add custom metadata to document chunks, such as titles or other relevant information, might improve the retrieved results in some use cases.
- **Additional optional services**: Integrating more optional services, such as summarizing documents or pre-processing documents before embedding them, could enhance the plugin's functionality and quality of retrieved results. These services could be implemented using language models and integrated directly into the plugin, rather than just being available in the scripts.

We welcome contributions from the community to help improve the ChatGPT Retrieval Plugin and expand its capabilities. If you have an idea or feature you'd like to contribute, please submit a pull request to the repository.

## Contributors

We would like to extend our gratitude to the following contributors for their code / documentation contributions, and support in integrating various vector database providers with the ChatGPT Retrieval Plugin:

- [Pinecone](https://www.pinecone.io/)
  - [acatav](https://github.com/acatav)
  - [gkogan](https://github.com/gkogan)
  - [jamescalam](https://github.com/jamescalam)
- [Weaviate](https://www.semi.technology/)
  - [byronvoorbach](https://github.com/byronvoorbach)
  - [hsm207](https://github.com/hsm207)
  - [sebawita](https://github.com/sebawita)
- [Zilliz](https://zilliz.com/)
  - [filip-halt](https://github.com/filip-halt)
- [Milvus](https://milvus.io/)
  - [filip-halt](https://github.com/filip-halt)
- [Qdrant](https://qdrant.tech/)
  - [kacperlukawski](https://github.com/kacperlukawski)
- [Redis](https://redis.io/)
  - [spartee](https://github.com/spartee)
  - [tylerhutcherson](https://github.com/tylerhutcherson)
