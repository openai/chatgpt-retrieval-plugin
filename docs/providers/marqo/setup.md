# Marqo

[Marqo](https://www.marqo.ai) is an end-to-end, multimodal vector search engine. With Marqo, users can store and query unstructured data such as text, images, and code through a single easy-to-use API. Input preprocessing, machine learning inference, and storage are all included out of the box and can be easily scaled. You can self host Marqo [with our open source docker](https://github.com/marqo-ai/marqo#getting-started) or you can [sign up to our cloud for a managed solution](https://www.marqo.ai/pricing).

We recommend starting with a prompt like the following to let ChatGPT know what it can do.
> Hey, you are connected to the retrieval plugin. It is using Marqo as the datastore, Marqo is able to work with images and text, you can include image URLs that I provide alongside text in your searches and marqo will be able to understand the image content. Understand?

The app will create a Marqo index for you automatically using the `MARQO_INDEX` environment variable, if it already exists then it will use the existing one.

**Environment Variables:**

| Name                                | Required | Description                                                                                                                           |
| ----------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `DATASTORE`                         | Yes      | Datastore name, set this to `marqo`                                                                                                |
| `BEARER_TOKEN`                      | Yes      | Your secret token for authenticating requests to the API                                                                              |
| `OPENAI_API_KEY`                    | No       | Marqo generates embeddings for you so this is not required                                                                            |
| `MARQO_API_URL`                     | Yes      | Your Marqo API URL. If running locally this will be `http://localhost:8882` by default, if using the cloud then this will be found in the [Marqo console](https://console.marqo.ai/)                                                      |
| `MARQO_API_KEY`                     | Maybe    | Your API key for Marqo, this is only required if you are using the managed cloud offering, keys are found in your [Marqo console](https://console.marqo.ai/)      |
| `MARQO_INDEX`                       | No       | Your chosen Marqo index name. **Note:** Index name must consist of lower case alphanumeric characters or '-'                          |
| `MARQO_INFERENCE_MODEL`             | No       | Your chosen Model for generating embeddings, [see our documentation](https://docs.marqo.ai/0.0.20/Models-Reference/dense_retrieval/)|
| `MARQO_UPSERT_BATCH_SIZE`           | No       | Batch size for bulk upserts                                                                                                           |
| `TREAT_URLS_AND_POINTERS_AS_IMAGES` | No       | `true` or `false`, if `true` then images will be downloaded and embedded. Requires that `MARQO_INFERENCE_MODEL` is a CLIP model. Defaults to `false`|

If you want more control over index creation or want to load your own custom inference models then this can be done through the Marqo API, [please refer to the documentation](https://docs.marqo.ai/latest/).

```python
# Creating index with Marqo's SDK - use only if you wish to create the index manually.
# NOTE: Not all of these settings are required, we provide the defaults here for visibility
import os
import marqo

mq = marqo.Client(url=os.environ['MARQO_API_URL'], api_key=os.environ['MARQO_API_KEY'])

settings = {
    "index_defaults": {
        "treat_urls_and_pointers_as_images": False,
        "model": "hf/all_datasets_v4_MiniLM-L6",
        "normalize_embeddings": True,
        "text_preprocessing": {
            "split_length": 2,
            "split_overlap": 0,
            "split_method": "sentence"
        },
        "image_preprocessing": {
            "patch_method": None
        },
        "ann_parameters" : {
            "space_type": "cosinesimil",
            "parameters": {
                "ef_construction": 128,
                "m": 16
            }
        }
    },
    "number_of_shards": 1
}

mq.create_index(os.environ['MARQO_INDEX'], settings_dict=settings)
```
