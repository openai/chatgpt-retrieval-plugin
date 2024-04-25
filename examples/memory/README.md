# ChatGPT Retrieval Plugin with Memory

This example demonstrates how to give ChatGPT the ability to remember information from conversations and store it in the retrieval plugin for later use. By allowing the model to access the `/upsert` endpoint, it can save snippets from the conversation to the vector database and retrieve them when needed.

## Setup

To enable ChatGPT to save information from conversations, follow these steps:

- Navigate to the "Configure" tab in the [create GPT page](https://chat.openai.com/gpts/editor), and copy the contents of [openapi.yaml](openapi.yaml) into the custom actions section. This will give the custom GPT access to both the Retrieval Plugin's query and upsert endpoints.

**Optional:** If you make any changes to the plugin instructions or metadata models, you can also copy the contents of [main.py](main.py) into the main [main.py](../../server/main.py) file. This will allow you to access the openapi.json at `http://0.0.0.0:8000/sub/openapi.json` when you run the app locally. You can convert from JSON to YAML format with [Swagger Editor](https://editor.swagger.io/). Alternatively, you can replace the openapi.yaml file with an openapi.json file.

After completing these steps, your custom GPT will be able to access your plugin's `/upsert` endpoint and save snippets from the conversation to the vector database. This enables the model to remember information from previous conversations and retrieve it when needed.
