# Pinecone

[Pinecone](https://www.pinecone.io) is a managed vector database built for speed, scale, and shipping to production sooner. To use Pinecone as your vector database provider, first get an API key by [signing up for an account](https://app.pinecone.io/). You can access your API key from the "API Keys" section in the sidebar of your dashboard. Pinecone also supports hybrid search and at the time of writing is the only datastore to support SPLADE sparse vectors natively.

A full Jupyter notebook walkthrough for the Pinecone flavor of the retrieval plugin can be found [here](https://github.com/openai/chatgpt-retrieval-plugin/blob/main/examples/providers/pinecone/semantic-search.ipynb). There is also a [video walkthrough here](https://youtu.be/hpePPqKxNq8).

The app will create a Pinecone index for you automatically when you run it for the first time. Just pick a name for your index and set it as an environment variable.

**Environment Variables:**

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
