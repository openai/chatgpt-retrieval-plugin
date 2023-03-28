# ChatGPT Retrieval Plugin

> **Join the [ChatGPT plugins waitlist here](https://openai.com/waitlist/plugins)!**

Find an example video of a Retrieval Plugin that has access to the UN Annual Reports from 2018 to 2022 [here](https://cdn.openai.com/chat-plugins/retrieval-gh-repo-readme/Retrieval-Final.mp4).

## Introduction

The ChatGPT Retrieval Plugin repository provides a flexible solution for semantic search and retrieval of personal or organizational documents using natural language queries. The repository is organized into several directories:

| Directory                     | Description                                                                                                      |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| [`datastore`](/datastore)     | Contains the core logic for storing and querying document embeddings using various vector database providers.    |
| [`examples`](/examples)       | Includes example configurations, authentication methods, and provider-specific examples.                         |
| [`models`](/models)           | Contains the data models used by the plugin, such as document and metadata models.                               |
| [`scripts`](/scripts)         | Provides scripts for processing and uploading documents from different data sources.                             |
| [`server`](/server)           | Houses the main FastAPI server implementation.                                                                   |
| [`services`](/services)       | Contains utility services for tasks like chunking, metadata extraction, and PII detection.                       |
| [`tests`](/tests)             | Includes integration tests for various vector database providers.                                                |
| [`.well-known`](/.well-known) | Stores the plugin manifest file and OpenAPI schema, which define the plugin configuration and API specification. |

This README provides detailed information on how to set up, develop, and deploy the ChatGPT Retrieval Plugin.

## Table of Contents

- [About](#about)
  - [Plugins](#plugins)
  - [Retrieval Plugin](#retrieval-plugin)
  - [Memory Feature](#memory-feature)
  - [Security](#security)
  - [API Endpoints](#api-endpoints)
- [Quickstart](#quickstart)
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
  - [Personalization](#personalization)
  - [Authentication Methods](#authentication-methods)
- [Deployment](#deployment)
  - [Deploying to Fly.io](#deploying-to-flyio)
  - [Deploying to Heroku](#deploying-to-heroku)
  - [Other Deployment Options](#other-deployment-options)
- [Webhooks](#webhooks)
- [Scripts](#scripts)
- [Limitations](#limitations)
- [Contributors](#contributors)
- [Future Directions](#future-directions)

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
   <Add the environment variables for your chosen vector DB here>
   ```

9. Run the API locally: `poetry run start`
10. Access the API documentation at `http://0.0.0.0:8000/docs` and test the API endpoints (make sure to add your bearer token).

For more detailed information on setting up, developing, and deploying the ChatGPT Retrieval Plugin, refer to the full Development section below.

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

The plugin supports several vector database providers, each with different features, performance, and pricing. Depending on which one you choose, you will need to use a different Dockerfile and set different environment variables. The following sections provide detailed information and instructions on using each vector database provider.

#### Pinecone

[Pinecone](https://www.pinecone.io) is a managed vector database built for speed, scale, and shipping to production sooner. To use Pinecone as your vector database provider, first get an API key by [signing up for an account](https://app.pinecone.io/). You can access your API key from the "API Keys" section in the sidebar of your dashboard. Pinecone also supports hybrid search and at the time of writing is the only datastore to support SPLADE sparse vectors natively.

A full Jupyter notebook walkthrough for the Pinecone flavor of the retrieval plugin can be found [here](https://github.com/openai/chatgpt-retrieval-plugin/blob/main/examples/providers/pinecone/semantic-search.ipynb). There is also a [video walkthrough here](https://youtu.be/hpePPqKxNq8).

The app will create a Pinecone index for you automatically when you run it for the first time. Just pick a name for your index and set it as an environment variable.

Environment Variables:

| Name                   | Required | Description                                                                                                                      |
| ---------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `DATASTORE`            | Yes      | Datastore name, set this to `pinecone`                                                                                           |
| `BEARER_TOKEN`         | Yes      | Your secret token for authenticating requests to the API                                                                         |
| `OPENAI_API_KEY`       | Yes      | Your OpenAI API key for generating embeddings with the `text-embedding-ada-002` model                                            |
| `PINECONE_API_KEY`     | Yes      | Your Pinecone API key, found in the [Pinecone console](https://app.pinecone.io/)                                                 |
| `PINECONE_ENVIRONMENT` | Yes      | Your Pinecone environment, found in the [Pinecone console](https://app.pinecone.io/), e.g. `us-west1-gcp`, `us-east-1-aws`, etc. |
| `PINECONE_INDEX`       | Yes      | Your chosen Pinecone index name. **Note:** Index name must consist of lower case alphanumeric characters or '-'                  |

If you want to create your own index with custom configurations, you can do so using the Pinecone SDK, API, or web interface ([see docs](https://docs.pinecone.io/docs/manage-indexes)). Make sure to use a dimensionality of 1536 for the embeddings and avoid indexing on the text field in the metadata, as this will reduce the performance significantly.

```python
# Creating index with Pinecone SDK - use only if you wish to create the index manually.

import os, pinecone

pinecone.init(api_key=os.environ['PINECONE_API_KEY'],
              environment=os.environ['PINECONE_ENVIRONMENT'])

pinecone.create_index(name=os.environ['PINECONE_INDEX'],
                      dimension=1536,
                      metric='cosine',
                      metadata_config={
                          "indexed": ['source', 'source_id', 'url', 'created_at', 'author', 'document_id']})
```

#### Weaviate

##### Set up a Weaviate Instance

Weaviate is an open-source vector search engine designed to scale seamlessly into billions of data objects. This implementation supports hybrid search out-of-the-box (meaning it will perform better for keyword searches).

You can run Weaviate in 4 ways:

- **SaaS** – with [Weaviate Cloud Services (WCS)](https://weaviate.io/pricing).

  WCS is a fully managed service that takes care of hosting, scaling, and updating your Weaviate instance. You can try it out for free with a sandbox that lasts for 30 days.

  To set up a SaaS Weaviate instance with WCS:

  1.  Navigate to [Weaviate Cloud Console](https://console.weaviate.io/).
  2.  Register or sign in to your WCS account.
  3.  Create a new cluster with the following settings:
      - `Name` – a unique name for your cluster. The name will become part of the URL used to access this instance.
      - `Subscription Tier` – Sandbox for a free trial, or contact [hello@weaviate.io](mailto:hello@weaviate.io) for other options.
      - `Weaviate Version` - The latest version by default.
      - `OIDC Authentication` – Enabled by default. This requires a username and password to access your instance.
  4.  Wait for a few minutes until your cluster is ready. You will see a green tick ✔️ when it's done. Copy your cluster URL.

- **Hybrid SaaS**

  > If you need to keep your data on-premise for security or compliance reasons, Weaviate also offers a Hybrid SaaS option: Weaviate runs within your cloud instances, but the cluster is managed remotely by Weaviate. This gives you the benefits of a managed service without sending data to an external party.

  The Weaviate Hybrid SaaS is a custom solution. If you are interested in this option, please reach out to [hello@weaviate.io](mailto:hello@weaviate.io).

- **Self-hosted** – with a Docker container

  To set up a Weaviate instance with Docker:
  1. [Install Docker](https://docs.docker.com/engine/install/) on your local machine if it is not already installed.
  2. [Install the Docker Compose Plugin](https://docs.docker.com/compose/install/)
  3.  Download a `docker-compose.yml` file with this `curl` command:

      ```
      curl -o docker-compose.yml "https://configuration.weaviate.io/v2/docker-compose/docker-compose.yml?modules=standalone&runtime=docker-compose&weaviate_version=v1.18.0"
      ```

      Alternatively, you can use Weaviate's docker compose [configuration tool](https://weaviate.io/developers/weaviate/installation/docker-compose) to generate your own `docker-compose.yml` file.

  4.  Run `docker compose up -d` to spin up a Weaviate instance.

      > To shut it down, run `docker compose down`.

- **Self-hosted** – with a Kubernetes cluster

  To configure a self-hosted instance with Kubernetes, follow Weaviate's [documentation](https://weaviate.io/developers/weaviate/installation/kubernetes).

##### Configure Weaviate Environment Variables

You need to set some environment variables to connect to your Weaviate instance.

**Retrieval App Environment Variables**

| Name             | Required | Description                            |
| ---------------- | -------- | -------------------------------------- |
| `DATASTORE`      | Yes      | Datastore name. Set this to `weaviate` |
| `BEARER_TOKEN`   | Yes      | Your secret token                      |
| `OPENAI_API_KEY` | Yes      | Your OpenAI API key                    |

**Weaviate Datastore Environment Variables**

| Name             | Required | Description                                                        | Default            |
| ---------------- | -------- | ------------------------------------------------------------------ | ------------------ |
| `WEAVIATE_HOST`  | Optional | Your Weaviate instance host address (see notes below)              | `http://127.0.0.1` |
| `WEAVIATE_PORT`  | Optional | Your Weaviate port number                                          | 8080               |
| `WEAVIATE_INDEX` | Optional | Your chosen Weaviate class/collection name to store your documents | OpenAIDocument     |

> For **WCS instances**, set `WEAVIATE_PORT` to 443 and `WEAVIATE_HOST` to `https://(wcs-instance-name).weaviate.network`. For example: `https://my-project.weaviate.network/`.

> For **self-hosted instances**, if your instance is not at 127.0.0.1:8080, set `WEAVIATE_HOST` and `WEAVIATE_PORT` accordingly. For example: `WEAVIATE_HOST=http://localhost/` and `WEAVIATE_PORT=4040`.

**Weaviate Auth Environment Variables**

If you enabled OIDC authentication for your Weaviate instance (recommended for WCS instances), set the following environment variables. If you enabled anonymous access, skip this section.

| Name                | Required | Description                    |
| ------------------- | -------- | ------------------------------ |
| `WEAVIATE_USERNAME` | Yes      | Your OIDC or WCS username      |
| `WEAVIATE_PASSWORD` | Yes      | Your OIDC or WCS password      |
| `WEAVIATE_SCOPES`   | Optional | Space-separated list of scopes |

Learn more about [authentication in Weaviate](https://weaviate.io/developers/weaviate/configuration/authentication#overview) and the [Python client authentication](https://weaviate-python-client.readthedocs.io/en/stable/weaviate.auth.html).

**Weaviate Batch Import Environment Variables**

Weaviate uses a batching mechanism to perform operations in bulk. This makes importing and updating your data faster and more efficient. You can adjust the batch settings with these optional environment variables:

| Name                             | Required | Description                                                  | Default |
| -------------------------------- | -------- | ------------------------------------------------------------ | ------- |
| `WEAVIATE_BATCH_SIZE`            | Optional | Number of insert/updates per batch operation                 | 20      |
| `WEAVIATE_BATCH_DYNAMIC`         | Optional | Lets the batch process decide the batch size                 | False   |
| `WEAVIATE_BATCH_TIMEOUT_RETRIES` | Optional | Number of retry-on-timeout attempts                          | 3       |
| `WEAVIATE_BATCH_NUM_WORKERS`     | Optional | The max number of concurrent threads to run batch operations | 1       |

> **Note:** The optimal `WEAVIATE_BATCH_SIZE` depends on the available resources (RAM, CPU). A higher value means faster bulk operations, but also higher demand for RAM and CPU. If you experience failures during the import process, reduce the batch size.

> Setting `WEAVIATE_BATCH_SIZE` to `None` means no limit to the batch size. All insert or update operations would be sent to Weaviate in a single operation. This might be risky, as you lose control over the batch size.

Learn more about [batch configuration in Weaviate](https://weaviate.io/developers/weaviate/client-libraries/python#batch-configuration).

#### Zilliz

Zilliz is a managed cloud-native vector database designed for the billion scale. Zilliz offers many key features, such as:

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

##### Deploying the Database

Zilliz Cloud is deployable in a few simple steps. First, create an account [here](https://cloud.zilliz.com/signup). Once you have an account set up, follow the guide [here](https://zilliz.com/doc/quick_start) to set up a database and get the parameters needed for this application.

Environment Variables:

| Name                | Required | Description                                       |
| ------------------- | -------- | ------------------------------------------------- |
| `DATASTORE`         | Yes      | Datastore name, set to `zilliz`                   |
| `BEARER_TOKEN`      | Yes      | Your secret token                                 |
| `OPENAI_API_KEY`    | Yes      | Your OpenAI API key                               |
| `ZILLIZ_COLLECTION` | Optional | Zilliz collection name. Defaults to a random UUID |
| `ZILLIZ_URI`        | Yes      | URI for the Zilliz instance                       |
| `ZILLIZ_USER`       | Yes      | Zilliz username                                   |
| `ZILLIZ_PASSWORD`   | Yes      | Zilliz password                                   |

#### Running Zilliz Integration Tests

A suite of integration tests is available to verify the Zilliz integration. To run the tests, create a Zilliz database and update the environment variables.

Then, launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/zilliz/test_zilliz_datastore.py
```

#### Milvus

Milvus is the open-source, cloud-native vector database that scales to billions of vectors. It's the open-source version of Zilliz. It supports:

- Various indexing algorithms and distance metrics
- Scalar filtering and time travel searches
- Rollback and snapshots
- Multi-language SDKs
- Storage and compute separation
- Cloud scalability
- A developer-first community with multi-language support

Visit the [Github](https://github.com/milvus-io/milvus) to learn more.

##### Deploying the Database

You can deploy and manage Milvus using Docker Compose, Helm, K8's Operator, or Ansible. Follow the instructions [here](https://milvus.io/docs) to get started.

Environment Variables:

| Name                | Required | Description                                            |
| ------------------- | -------- | ------------------------------------------------------ |
| `DATASTORE`         | Yes      | Datastore name, set to `milvus`                        |
| `BEARER_TOKEN`      | Yes      | Your bearer token                                      |
| `OPENAI_API_KEY`    | Yes      | Your OpenAI API key                                    |
| `MILVUS_COLLECTION` | Optional | Milvus collection name, defaults to a random UUID      |
| `MILVUS_HOST`       | Optional | Milvus host IP, defaults to `localhost`                |
| `MILVUS_PORT`       | Optional | Milvus port, defaults to `19530`                       |
| `MILVUS_USER`       | Optional | Milvus username if RBAC is enabled, defaults to `None` |
| `MILVUS_PASSWORD`   | Optional | Milvus password if required, defaults to `None`        |

#### Running Milvus Integration Tests

A suite of integration tests is available to verify the Milvus integration. To run the tests, run the milvus docker compose found in the examples folder.

Then, launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/milvus/test_milvus_datastore.py
```

#### Qdrant

Qdrant is a vector database that can store documents and vector embeddings. It can run as a self-hosted version or a managed [Qdrant Cloud](https://cloud.qdrant.io/)
solution. The configuration is almost identical for both options, except for the API key that [Qdrant Cloud](https://cloud.qdrant.io/) provides.

Environment Variables:

| Name                | Required | Description                                                 | Default            |
| ------------------- | -------- | ----------------------------------------------------------- | ------------------ |
| `DATASTORE`         | Yes      | Datastore name, set to `qdrant`                             |                    |
| `BEARER_TOKEN`      | Yes      | Secret token                                                |                    |
| `OPENAI_API_KEY`    | Yes      | OpenAI API key                                              |                    |
| `QDRANT_URL`        | Yes      | Qdrant instance URL                                         | `http://localhost` |
| `QDRANT_PORT`       | Optional | TCP port for Qdrant HTTP communication                      | `6333`             |
| `QDRANT_GRPC_PORT`  | Optional | TCP port for Qdrant GRPC communication                      | `6334`             |
| `QDRANT_API_KEY`    | Optional | Qdrant API key for [Qdrant Cloud](https://cloud.qdrant.io/) |                    |
| `QDRANT_COLLECTION` | Optional | Qdrant collection name                                      | `document_chunks`  |

##### Qdrant Cloud

For a hosted [Qdrant Cloud](https://cloud.qdrant.io/) version, provide the Qdrant instance
URL and the API key from the [Qdrant Cloud UI](https://cloud.qdrant.io/).

**Example:**

```bash
QDRANT_URL="https://YOUR-CLUSTER-URL.aws.cloud.qdrant.io"
QDRANT_API_KEY="<YOUR_QDRANT_CLOUD_CLUSTER_API_KEY>"
```

The other parameters are optional and can be changed if needed.

##### Self-hosted Qdrant Instance

For a self-hosted version, use Docker containers or the official Helm chart for deployment. The only
required parameter is the `QDRANT_URL` that points to the Qdrant server URL.

**Example:**

```bash
QDRANT_URL="http://YOUR_HOST.example.com:6333"
```

The other parameters are optional and can be changed if needed.

##### Running Qdrant Integration Tests

A suite of integration tests verifies the Qdrant integration. To run it, start a local Qdrant instance in a Docker container.

```bash
docker run -p "6333:6333" -p "6334:6334" qdrant/qdrant:v1.0.3
```

Then, launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/qdrant/test_qdrant_datastore.py
```

#### Redis

Redis is a real-time data platform that supports a variety of use cases for everyday applications as well as AI/ML workloads. Use Redis as a low-latency vector engine by creating a Redis database with the [Redis Stack docker container](/examples/docker/redis/docker-compose.yml). For a hosted/managed solution, try [Redis Cloud](https://app.redislabs.com/#/). See more helpful examples of Redis as a vector database [here](https://github.com/RedisVentures/redis-ai-resources).

- The database **needs the RediSearch module (>=v2.6) and RedisJSON**, which are included in the self-hosted docker compose above.
- Run the App with the Redis docker image: `docker compose up -d` in [this dir](/examples/docker/redis/).
- The app automatically creates a Redis vector search index on the first run. Optionally, create a custom index with a specific name and set it as an environment variable (see below).
- To enable more hybrid searching capabilities, adjust the document schema [here](/datastore/providers/redis_datastore.py).


Environment Variables:

| Name                    | Required | Description                                                                                                            | Default     |
| ----------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------- | ----------- |
| `DATASTORE`             | Yes      | Datastore name, set to `redis`                                                                                         |             |
| `BEARER_TOKEN`          | Yes      | Secret token                                                                                                           |             |
| `OPENAI_API_KEY`        | Yes      | OpenAI API key                                                                                                         |             |
| `REDIS_HOST`            | Optional | Redis host url                                                                                                         | `localhost` |
| `REDIS_PORT`            | Optional | Redis port                                                                                                             | `6379`      |
| `REDIS_PASSWORD`        | Optional | Redis password                                                                                                         | none        |
| `REDIS_INDEX_NAME`      | Optional | Redis vector index name                                                                                                | `index`     |
| `REDIS_DOC_PREFIX`      | Optional | Redis key prefix for the index                                                                                         | `doc`       |
| `REDIS_DISTANCE_METRIC` | Optional | Vector similarity distance metric                                                                                      | `COSINE`    |
| `REDIS_INDEX_TYPE`      | Optional | [Vector index algorithm type](https://redis.io/docs/stack/search/reference/vectors/#creation-attributes-per-algorithm) | `FLAT`      |

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

Before deploying your app, you might want to remove unused dependencies from your [pyproject.toml](/pyproject.toml) file to reduce the size of your app and improve its performance. Depending on the vector database provider you choose, you can remove the packages that are not needed for your specific provider.

Here are the packages you can remove for each vector database provider:

- **Pinecone:** Remove `weaviate-client`, `pymilvus`, `qdrant-client`, and `redis`.
- **Weaviate:** Remove `pinecone-client`, `pymilvus`, `qdrant-client`, and `redis`.
- **Zilliz:** Remove `pinecone-client`, `weaviate-client`, `qdrant-client`, and `redis`.
- **Milvus:** Remove `pinecone-client`, `weaviate-client`, `qdrant-client`, and `redis`.
- **Qdrant:** Remove `pinecone-client`, `weaviate-client`, `pymilvus`, and `redis`.
- **Redis:** Remove `pinecone-client`, `weaviate-client`, `pymilvus`, and `qdrant-client`.

After removing the unnecessary packages from the `pyproject.toml` file, you don't need to run `poetry lock` and `poetry install` manually. The provided Dockerfile takes care of installing the required dependencies using the `requirements.txt` file generated by the `poetry export` command.

Once you have deployed your app, consider uploading an initial batch of documents using one of [these scripts](/scripts) or by calling the `/upsert` endpoint, for example:

```bash
curl -X POST https://your-app-url.com/upsert \
  -H "Authorization: Bearer <your_bearer_token>" \
  -H "Content-type: application/json" \
  -d '{"documents": [{"id": "doc1", "text": "Hello world", "metadata": {"source_id": "12345", "source": "file"}}, {"text": "How are you?", "metadata": {"source_id": "23456"}}]}'
```

### Deploying to Fly.io

To deploy the Docker container from this repository to Fly.io, follow
these steps:

[Install Docker](https://docs.docker.com/engine/install/) on your local machine if it is not already installed.

Install the [Fly.io CLI](https://fly.io/docs/getting-started/installing-flyctl/) on your local machine.

Clone the repository from GitHub:

```
git clone https://github.com/openai/chatgpt-retrieval-plugin.git
```

Navigate to the cloned repository directory:

```
cd path/to/chatgpt-retrieval-plugin
```

Log in to the Fly.io CLI:

```
flyctl auth login
```

Create and launch your Fly.io app:

```
flyctl launch
```

Follow the instructions in your terminal:

- Choose your app name
- Choose your app region
- Don't add any databases
- Don't deploy yet (if you do, the first deploy might fail as the environment variables are not yet set)

Set the required environment variables:

```
flyctl secrets set DATASTORE=your_datastore \
OPENAI_API_KEY=your_openai_api_key \
BEARER_TOKEN=your_bearer_token \
<Add the environment variables for your chosen vector DB here>
```

Alternatively, you could set environment variables in the [Fly.io Console](https://fly.io/dashboard).

At this point, you can change the plugin url in your plugin manifest file [here](/.well-known/ai-plugin.json), and in your OpenAPI schema [here](/.well-known/openapi.yaml) to the url for your Fly.io app, which will be `https://your-app-name.fly.dev`.

Deploy your app with:

```
flyctl deploy
```

After completing these steps, your Docker container should be deployed to Fly.io and running with the necessary environment variables set. You can view your app by running:

```
flyctl open
```

which will open your app url. You should be able to find the OpenAPI schema at `<your_app_url>/.well-known/openapi.yaml` and the manifest at `<your_app_url>/.well-known/ai-plugin.json`.

To view your app logs:

```
flyctl logs
```

Now, make sure you have changed the plugin url in your plugin manifest file [here](/.well-known/ai-plugin.json), and in your OpenAPI schema [here](/.well-known/openapi.yaml), and redeploy with `flyctl deploy`. This url will be `https://<your-app-name>.fly.dev`.

**Debugging tips:**
Fly.io uses port 8080 by default.

If your app fails to deploy, check if the environment variables are set correctly, and then check if your port is configured correctly. You could also try using the [`-e` flag](https://fly.io/docs/flyctl/launch/) with the `flyctl launch` command to set the environment variables at launch.

### Deploying to Heroku

To deploy the Docker container from this repository to Heroku and set the required environment variables, follow these steps:

[Install Docker](https://docs.docker.com/engine/install/) on your local machine if it is not already installed.

Install the [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) on your local machine.

Clone the repository from GitHub:

```
git clone https://github.com/openai/chatgpt-retrieval-plugin.git
```

Navigate to the cloned repository directory:

```
cd path/to/chatgpt-retrieval-plugin
```

Log in to the Heroku CLI:

```
heroku login
```

Create a Heroku app:

```
heroku create [app-name]
```

Log in to the Heroku Container Registry:

```
heroku container:login
```

Alternatively, you can use a command from the Makefile to log in to the Heroku Container Registry by running:

```
make heroku-login
```

Build the Docker image using the Dockerfile:

```
docker buildx build --platform linux/amd64 -t [image-name] .
```

(Replace `[image-name]` with the name you want to give your Docker image)

Push the Docker image to the Heroku Container Registry, and release the newly pushed image to your Heroku app.

```
docker tag [image-name] registry.heroku.com/[app-name]/web
docker push registry.heroku.com/[app-name]/web
heroku container:release web -a [app-name]
```

Alternatively, you can use a command from the to push the Docker image to the Heroku Container Registry by running:

```
make heroku-push
```

**Note:** You will need to edit the Makefile and replace `<your app name>` with your actual app name.

Set the required environment variables for your Heroku app:

```
heroku config:set DATASTORE=your_datastore \
OPENAI_API_KEY=your_openai_api_key \
BEARER_TOKEN=your_bearer_token \
<Add the environment variables for your chosen vector DB here> \
-a [app-name]
```

You could also set environment variables in the [Heroku Console](https://dashboard.heroku.com/apps).

After completing these steps, your Docker container should be deployed to Heroku and running with the necessary environment variables set. You can view your app by running:

```
heroku open -a [app-name]
```

which will open your app url. You should be able to find the OpenAPI schema at `<your_app_url>/.well-known/openapi.yaml` and the manifest at `<your_app_url>/.well-known/ai-plugin.json`.

To view your app logs:

```
heroku logs --tail -a [app-name]
```

Now make sure to change the plugin url in your plugin manifest file [here](/.well-known/ai-plugin.json), and in your OpenAPI schema [here](/.well-known/openapi.yaml), and redeploy with `make heroku-push`. This url will be `https://your-app-name.herokuapp.com`.

### Other Deployment Options

Some possible other options for deploying the app are:

- Azure Container Apps: This is a cloud platform that allows you to deploy and manage web apps using Docker containers. You can use the Azure CLI or the Azure Portal to create and configure your app service, and then push your Docker image to a container registry and deploy it to your app service. You can also set environment variables and scale your app using the Azure Portal. Learn more [here](https://learn.microsoft.com/en-us/azure/container-apps/get-started-existing-container-image-portal?pivots=container-apps-private-registry).
- Google Cloud Run: This is a serverless platform that allows you to run stateless web apps using Docker containers. You can use the Google Cloud Console or the gcloud command-line tool to create and deploy your Cloud Run service, and then push your Docker image to the Google Container Registry and deploy it to your service. You can also set environment variables and scale your app using the Google Cloud Console. Learn more [here](https://cloud.google.com/run/docs/quickstarts/build-and-deploy).
- AWS Elastic Container Service: This is a cloud platform that allows you to run and manage web apps using Docker containers. You can use the AWS CLI or the AWS Management Console to create and configure your ECS cluster, and then push your Docker image to the Amazon Elastic Container Registry and deploy it to your cluster. You can also set environment variables and scale your app using the AWS Management Console. Learn more [here](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/docker-basics.html).

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
