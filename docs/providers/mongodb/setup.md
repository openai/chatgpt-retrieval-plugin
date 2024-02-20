# Setting up MongoDB Atlas as the Datastore Provider

MongoDB Atlas is a multi-cloud database service by the same people that build MongoDB. 
Atlas simplifies deploying and managing your databases while offering the versatility you need 
to build resilient and performant global applications on the cloud providers of your choice.

In the ChatGPT Retrieval Plugin, Atlas is used for its vector database 
providing the core logic for storing and querying document embeddings.

In the section, we set up a cluster, a database, test it, and finally create an Atlas Vector Search Index.

### Deploy a Free Cluster

Follow the [Getting-Started](https://www.mongodb.com/basics/mongodb-atlas-tutorial) documentation 
to create an account, deploy an Atlas cluster, and connect to a database.


### Connect to a database through the Python "driver" 

There are a number of ways to navigate the Atlas UI. Keep your eye out for "Connect" and "driver".

On the left panel, navigate and click 'Database' under DEPLOYMENT. 
Click the Connect button that appears, then Drivers. Select Python.
Have no concern for the version. This is the PyMongo, not Python, version.
Once you have got the Connect Window open, you will see an instruction to `pip install pymongo`.
You will also see a **connection string**.  
This is the `uri` that a `pymongo.MongoClient` uses to connect to the Database.

**IMPORTANT** When you deploy the ChatGPT Retrieval App, this will be stored as the environment variable: `MONGODB_URI`  
It will look something like the following. The username and password, if not provided,
can be configured in **Database Access** under Security in the left panel. 

```
export MONGODB_URI="mongodb+srv://<username>:<password>@chatgpt-retrieval-plugin.zeatahb.mongodb.net/?retryWrites=true&w=majority"
```

### Test the connection

Atlas provides a simple check. Once you have your `uri` and `pymongo` installed, try the following in the python console.

```python
from pymongo.mongo_client import MongoClient
client = MongoClient(uri)  # Create a new client and connect to the server
try:
    client.admin.command('ping')  # Send a ping to confirm a successful connection
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
```

**Troubleshooting**
* You can edit a Database's users and passwords on the 'Database Access' page, under Security.
* Remember to add your IP address. (Try `curl -4 ifconfig.co`)

### Create an Atlas Vector Search Index

The final step to configure MongoDB as the Datastore is to create a Vector Search Index.
The procedure is described [here](https://www.mongodb.com/docs/atlas/atlas-vector-search/create-index/#procedure).

Under Services on the left panel, choose Atlas Search

The Plugin expects the following index definition.

```json
{
  "fields": [
    {
      "numDimensions": 1536,
      "path": "embedding",
      "similarity": "cosine",
      "type": "vector"
    }
  ]
}
```


### Set Datastore Environment Variables

To establish a connection to the MongoDB database and collection, define the following environment variables.
You can confirm that the required ones have been set like this:  `assert "MONGODB_URI" in os.environ`

| Name                  | Required | Description                                    |
| --------------------- |----------|------------------------------------------------|
| `MONGODB_URI`      | Yes      | Your MongoDB URI.                              |
| `MONGODB_INDEX` | Yes      | Your chosen MongoDB index name.                |
| `MONGODB_DATABASE` | No       | Your MongoDB Database. Defaults to 'default'.  |
| `MONGODB_COLLECTION` | No       | Your MongoDB Collection. Defaults to 'default' |
| `DATASTORE`           | Yes      | Datastore name, set this to `mongodb`          |


### Running MongoDB Integration Tests

A suite of integration tests is available to verify the Mongodb integration. The test suite needs the enviroment variables descripted above.

Then, launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/mongodb_atlas/test_mongodb_datastore.py
```
