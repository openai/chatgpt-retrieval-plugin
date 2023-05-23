
# Searchium
[Searchium](https://searchium.ai) is a cloud platform that performs high-speed vector searches using in-memory compute. Searchium allows you to store a vector embeddings database along with associated metadata.

## Setup
The basic flow consists of the following steps:
* Create a dataset.
* Add data to the dataset.
* Train/Index the dataset.
* Load the dataset onto the APU accelerator (Associative Processing Unit).
* Perform a search.
----

**Note: To perform fast vector searches, we use hardware accelerator called "APU" which requires data pre-processing(train and load), 
which improve search results significantly (The actual minimum dataset size should be above 4,000 records).
In our implementation of the datastore, we use a trigger called `SEARCHIUM_DATASET_SIZE` to automatically
initiate the training and loading processes. However, you can also perform these processes manually using our 
client or cloud interface as needed."** 

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


**The actual minimum dataset size should be at least 4,001.**

**Searchium cloud platform**
To start using our client, [sign up at searchium.ai](https://app.searchium.ai/signup). 
A free tier is available.
Afterward, you can retrieve your `SEARCHIUM_INSTANCE_ID` and `SEARCHIUM_CLIENT_API_URL` from your account:
 * Sign in -> Skip for now -> Skip for now again
 * API settings -> Create instance -> Launch Instance.
 

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