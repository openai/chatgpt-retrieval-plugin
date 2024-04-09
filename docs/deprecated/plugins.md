## Plugins (deprecated)

Plugins are chat extensions designed specifically for language models like ChatGPT, enabling them to access up-to-date information, run computations, or interact with third-party services in response to a user's request. They unlock a wide range of potential use cases and enhance the capabilities of language models.

Developers can create a plugin by exposing an API through their website and providing a standardized manifest file that describes the API. ChatGPT consumes these files and allows the AI models to make calls to the API defined by the developer.

A plugin consists of:

- An API
- An API schema (OpenAPI JSON or YAML format)
- A manifest (JSON file) that defines relevant metadata for the plugin

The Retrieval Plugin already contains all of these components. Read the Chat Plugins blogpost [here](https://openai.com/blog/chatgpt-plugins), and find the docs [here](https://platform.openai.com/docs/plugins/introduction).

To access the plugins model, navigate [here](https://chat.openai.com/?model=gpt-4-plugins).

### Testing a Localhost Plugin in ChatGPT

To test a localhost plugin in ChatGPT, use the provided [`local_server/main.py`](/local_server/main.py) file, which is specifically configured for localhost testing with CORS settings, no authentication and routes for the manifest, OpenAPI schema and logo.

Follow these steps to test your localhost plugin:

1. Run the localhost server using the `poetry run dev` command. This starts the server at the default address (e.g. `localhost:3333`).

2. Visit [ChatGPT](https://chat.openai.com/), select "Plugins" from the model picker, click on the plugins picker, and click on "Plugin store" at the bottom of the list.

3. Choose "Develop your own plugin" and enter your localhost URL (e.g. `localhost:3333`) when prompted.

4. Your localhost plugin is now enabled for your ChatGPT session.

For more information, refer to the [OpenAI documentation](https://platform.openai.com/docs/plugins/getting-started/openapi-definition).

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
