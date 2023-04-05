# Typesense

[Typesense](https://typesense.org) is an open source, in-memory search engine, that you can either [self-host](https://typesense.org/docs/guide/install-typesense.html#option-2-local-machine-self-hosting) or run on [Typesense Cloud](https://cloud.typesense.org). 

It focuses on performance by storing the entire index in RAM (with a backup on disk) and also focuses on providing an out-of-the-box developer experience by simplifying available options and setting good defaults. 

It also lets you combine attribute-based filtering together with vector queries.

The app will create a Typesense collection index for you automatically when you run it for the first time. Just pick a name for your collection and set it as an environment variable.

**Environment Variables:**

| Name                        | Required | Description                                                                                                                                                          |
|-----------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `DATASTORE`                 | Yes      | Datastore name, set this to `typesense`                                                                                                                              |
| `BEARER_TOKEN`              | Yes      | Your secret token for authenticating requests to the API                                                                                                             |
| `OPENAI_API_KEY`            | Yes      | Your OpenAI API key for generating embeddings with the `text-embedding-ada-002` model                                                                                |
| `TYPESENSE_HOST`            | Yes      | Your Typesense cluster's hostname. For eg: `localhost` or if you're on Typesense Cloud `xxx.a1.typesense.net` (you can get this value from your cluster's dashboard. |
| `TYPESENSE_PROTOCOL`        | Yes      | Your Typesense cluster's protocol. `http` or `https`. For Typesense Cloud use `https`.                                                                               |
| `TYPESENSE_PORT`            | Yes      | Your Typesense cluster's port. Eg: `8108`. For Typesense Cloud use `443`.                                                                                            |
| `TYPESENSE_COLLECTION_NAME` | Yes      | Your Typesense collection's name.                                                                                                                                    |

If you want to create your own collection with custom configurations, you can do so using the Typesense API, or web interface ([see docs](https://typesense.org/docs/0.24.1/api/collections.html#create-a-collection)).