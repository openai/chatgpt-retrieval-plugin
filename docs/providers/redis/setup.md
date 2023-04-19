# Redis

[Redis](https://redis.com/solutions/use-cases/vector-database/) is a real-time data platform that supports a variety of use cases for everyday applications as well as AI/ML workloads. Use Redis as a low-latency vector engine by creating a Redis database with the [Redis Stack docker container](/examples/docker/redis/docker-compose.yml). For a hosted/managed solution, try [Redis Cloud](https://app.redislabs.com/#/). See more helpful examples of Redis as a vector database [here](https://github.com/RedisVentures/redis-ai-resources).

- The database **needs the RediSearch module (>=v2.6) and RedisJSON**, which are included in the self-hosted docker compose above.
- Run the App with the Redis docker image: `docker compose up -d` in [this dir](/examples/docker/redis/).
- The app automatically creates a Redis vector search index on the first run. Optionally, create a custom index with a specific name and set it as an environment variable (see below).
- To enable more hybrid searching capabilities, adjust the document schema [here](/datastore/providers/redis_datastore.py).

**Environment Variables:**

| Name                    | Required | Description                                                                                                            | Default     |
| ----------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------- | ----------- |
| `DATASTORE`             | Yes      | Datastore name, set to `redis`                                                                                         |             |
| `BEARER_TOKEN`          | Yes      | Secret token                                                                                                           |             |
| `OPENAI_API_KEY`        | Yes      | OpenAI API key                                                                                                         |             |
| `REDIS_HOST`            | Optional | Redis host url                                                                                                         | `localhost` |
| `REDIS_PORT`            | Optional | Redis port                                                                                                             | `6379`      |
| `REDIS_PASSWORD`        | Optional | Redis password                                                                                                         | none        |
| `REDIS_INDEX_NAME`      | Optional | Redis vector index name                                                                                                | `index`     |
| `REDIS_DOC_PREFIX`      | Optional | Redis key prefix for the index                                                                                         | `doc`       |
| `REDIS_DISTANCE_METRIC` | Optional | Vector similarity distance metric                                                                                      | `COSINE`    |
| `REDIS_INDEX_TYPE`      | Optional | [Vector index algorithm type](https://redis.io/docs/stack/search/reference/vectors/#creation-attributes-per-algorithm) | `FLAT`      |


## Redis Datastore development & testing
In order to test your changes to the Redis Datastore, you can run the following commands:

```bash
# Run the Redis stack docker image
docker run -it --rm -p 6379:6379 redis/redis-stack-server:latest
```
    
```bash
# Run the Redis datastore tests
poetry run pytest -s ./tests/datastore/providers/redis/test_redis_datastore.py
```