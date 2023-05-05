### Setting up OpenSearch Datastore

You can use the docker-compose.yml file to create a local opensearch cluster. This is a great cluster for doing the testing as this creates a local cluster without security. In the production we would ideally like to create a security and SSL enabled cluster.

#### Starting the OpenSearch DataStore without security
1. Remove any old containers if present. 
```
docker-compose rm -f
```
2. Run the compose command to start the Datastore. Wait for 1-2 minutes for the container to start.
```
docker-compose up -d
```
3. Validate Datastore is running.
```
 curl http://localhost:9200
```
```
 Sample response:
 
 {
  "name" : "opensearch-node1",
  "cluster_name" : "opensearch-cluster",
  "cluster_uuid" : "e-AhrliiSgObpVH4_-xzaw",
  "version" : {
    "distribution" : "opensearch",
    "number" : "2.6.0",
    "build_type" : "tar",
    "build_hash" : "7203a5af21a8a009aece1474446b437a3c674db6",
    "build_date" : "2023-02-24T18:57:04.388618985Z",
    "build_snapshot" : false,
    "lucene_version" : "9.5.0",
    "minimum_wire_compatibility_version" : "7.10.0",
    "minimum_index_compatibility_version" : "7.0.0"
  },
  "tagline" : "The OpenSearch Project: https://opensearch.org/"
}
```

#### Starting the OpenSearch DataStore with Security
1. Remove any old containers if present.
```
docker-compose rm -f
```
2. Run the compose command to start the Datastore. Wait for 1-2 minutes for the container to start.
```
docker-compose -f secure-docker-compose.yml up -d
```
3. Validate Datastore is running.
```
 curl https://localhost:9500 -ku 'admin:admin'
```
```
 Sample response:
 
{
  "name" : "opensearch-secure-node1",
  "cluster_name" : "opensearch-cluster-secure",
  "cluster_uuid" : "9x5B06WgTtSeVdXARIIleQ",
  "version" : {
    "distribution" : "opensearch",
    "number" : "2.6.0",
    "build_type" : "tar",
    "build_hash" : "7203a5af21a8a009aece1474446b437a3c674db6",
    "build_date" : "2023-02-24T18:57:04.388618985Z",
    "build_snapshot" : false,
    "lucene_version" : "9.5.0",
    "minimum_wire_compatibility_version" : "7.10.0",
    "minimum_index_compatibility_version" : "7.0.0"
  },
  "tagline" : "The OpenSearch Project: https://opensearch.org/"
}
```

### Reference Links
* [OpenSearch Website](https://opensearch.org/)
* [Downloads](https://opensearch.org/downloads.html).
* [Documentation](https://opensearch.org/docs/)
* [K-NN Documentation](https://opensearch.org/docs/search-plugins/knn/index/)
* [OpenSearch Cluster setup with Docker](https://opensearch.org/docs/latest/install-and-configure/install-opensearch/docker/#deploy-an-opensearch-cluster-using-docker-compose)
* [K-NN Performance Tunning](https://opensearch.org/docs/latest/search-plugins/knn/performance-tuning/)
