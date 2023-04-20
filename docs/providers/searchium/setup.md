
# Searchium
In general, [Searchium](https://searchium.ai) is a cloud platform that performs fast vector searches.
Searchium allows you to store a vector embeddings database along with associated metadata.

## Setup
The basic flow consists of the following steps:
* Create a dataset.
* Add data to the dataset.
* Train the dataset.
* Load the dataset to the APU card (Associative Process Unit).
* Perform a search.
----
Note: To perform fast vector searches, we use hardware accelerator called "APU" which requires data pre-processing(train and load), 
which improve search results significantly.
In our implementation of the datastore, we use a trigger called `SEARCHIUM_DATASET_SIZE` to automatically
initiate the training and loading processes. However, you can also perform these processes manually using our 
client or cloud interface as needed." 
----

**Retrieval App Environment Variables**

| Name             | Required | Description                             |
| ---------------- | -------- |-----------------------------------------|
| `DATASTORE`      | Yes      | Datastore name. Set this to `searchium` |
| `BEARER_TOKEN`   | Yes      | Your secret token                       |
| `OPENAI_API_KEY` | Yes      | Your OpenAI API key                     |

**Searchium Vector Datastore Environment Variables**

| Name                            | Required | Description                                  | Default            |
| ------------------------------- |----------|----------------------------------------------| ------------------ |
| `SEARCHIUM_INSTANCE_ID`         | Yes      | Instance ID  (see below for details)         | None      |
| `SEARCHIUM_DATASET_SIZE`         | Yes      | Vector dataset size (see above for details)  | None               |
| `SEARCHIUM_CLIENT_API_URL`         | Yes      | API URL in Searchium cloud platform | None               |
| `SEARCHIUM_DATASET_ID`           | Yes      | Vector dataset ID (UUID)                     | None          | 


**Searchium cloud platform**
To start using our client, you need to [sign up at searchium.ai](https://app.searchium.ai/signup). 
You can use the free tier for a few hours. 
Afterward, you can retrieve your `SEARCHIUM_INSTANCE_ID` and `SEARCHIUM_CLIENT_API_URL` in your account.
Read more details on [searchium.ai](https://searchium.ai/).

```python
import os
import searchium

SEARCHIUM_INSTANCE_ID = os.environ.get("SEARCHIUM_INSTANCE_ID")
SEARCHIUM_DATASET_SIZE = os.environ.get("SEARCHIUM_DATASET_SIZE")
SEARCHIUM_CLIENT_API_URL = os.environ.get("SEARCHIUM_CLIENT_API_URL")
SEARCHIUM_DATASET_ID = os.environ.get("SEARCHIUM_DATASET_ID")

searchium.init(SEARCHIUM_INSTANCE_ID, SEARCHIUM_CLIENT_API_URL)
searchium.create_dataset(SEARCHIUM_DATASET_ID)
```