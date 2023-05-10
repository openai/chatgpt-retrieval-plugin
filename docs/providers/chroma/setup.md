[Chroma](https://trychroma.com) is an AI-native open-source embedding database designed to make it easy to work with embeddings. Chroma runs in-memory, or in a client-server setup.

Install Chroma by running `pip install chromadb`. Once installed, the core API consists of four essential commands for creating collections, adding embeddings, documents, and metadata, and querying embeddings to find similar documents. Get started with Chroma by visiting the [Getting Started](https://docs.trychroma.com) page on their documentation website, or explore the open-source code on their [GitHub repository](https://github.com/chroma-core/chroma).

**Chroma Environment Variables**

To set up Chroma and start using it as your vector database provider, you need to define some environment variables to connect to your Chroma instance.

**Chroma Datastore Environment Variables**

Chroma runs _in-memory_ by default, with local persistence. It can also run in [self-hosted](https://docs.trychroma.com/usage-guide#running-chroma-in-clientserver-mode) client-server mode, with a fully managed hosted version coming soon.

| Name                     | Required | Description                                                                                        | Default          |
| ------------------------ | -------- | -------------------------------------------------------------------------------------------------- | ---------------- |
| `DATASTORE`              | Yes      | Datastore name. Set this to `chroma`                                                               |                  |
| `BEARER_TOKEN`           | Yes      | Your secret token for authenticating requests to the API                                           |                  |
| `OPENAI_API_KEY`         | Yes      | Your OpenAI API key for generating embeddings                                                      |                  |
| `CHROMA_COLLECTION`      | Optional | Your chosen Chroma collection name to store your embeddings                                        | openaiembeddings |
| `CHROMA_IN_MEMORY`       | Optional | If set to `True`, ignore `CHROMA_HOST` and `CHROMA_PORT` and just use an in-memory Chroma instance | `True`           |
| `CHROMA_PERSISTENCE_DIR` | Optional | If set, and `CHROMA_IN_MEMORY` is set, persist to and load from this directory.                    | `openai`         |

To run Chroma in self-hosted client-server mode, st the following variables:

| Name          | Required | Description                                         | Default            |
| ------------- | -------- | --------------------------------------------------- | ------------------ |
| `CHROMA_HOST` | Optional | Your Chroma instance host address (see notes below) | `http://127.0.0.1` |
| `CHROMA_PORT` | Optional | Your Chroma port number                             | `8000`             |

> For **self-hosted instances**, if your instance is not at 127.0.0.1:8000, set `CHROMA_HOST` and `CHROMA_PORT` accordingly. For example: `CHROMA_HOST=http://localhost/` and `CHROMA_PORT=8080`.
