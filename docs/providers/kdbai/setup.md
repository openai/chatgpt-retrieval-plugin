# KDB.AI

[KDB.AI](https://kdb.ai) is a powerful knowledge-based vector database and search engine that allows developers to build scalable, reliable and real-time applications by providing advanced search, recommendation and personalization for AI applications, using real-time data. You can register for Free Trial on https://kdb.ai.

You can find a sample notebook to use the ChatGPT Retrieval Plugin backed by KDB.AI vector database [here](https://github.com/KxSystems/chatgpt-retrieval-plugin/blob/KDB.AI/examples/providers/kdbai/ChatGPT_QA_Demo.ipynb) and instructions to get started [here](https://code.kx.com/kdbai/integrations/openai.html).

**Environment Variables:**

| Name                | Required | Description                                                 | Default            |
| ------------------- | -------- | ----------------------------------------------------------- | ------------------ |
| `DATASTORE`         | Yes      | Datastore name, set to `kdbai`                              |                    |
| `BEARER_TOKEN`      | Yes      | Secret token                                                |                    |
| `OPENAI_API_KEY`    | Yes      | OpenAI API key                                              |                    |
| `KDBAI_ENDPOINT`    | Yes      | KDB.AI endpoint                                             |                    |
| `KDBAI_API_KEY`     | Yes      | KDB.AI API key                                              |                    |
| `KDBAI_TABLE`       | Optional | TCP port for Qdrant GRPC communication                      | `documents`        |
