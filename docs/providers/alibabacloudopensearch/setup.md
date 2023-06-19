# Alibaba Cloud OpenSearch

[Alibaba Cloud OpenSearch](https://www.alibabacloud.com/product/opensearch?spm=a3c0i.24291077.6791778070.126.79176df571ilTO) is a one-stop platform to develop intelligent search services. OpenSearch was built based on the large-scale distributed search engine developed by Alibaba. OpenSearch serves more than 500 business cases in Alibaba Group and thousands of Alibaba Cloud customers. OpenSearch helps develop search services in different search scenarios, including e-commerce, O2O, multimedia, the content industry, communities and forums, and big data query in enterprises.


**Environment Variables:**

| Name                      | Required | Description                                              | Default           |
| ------------------------- | -------- | -------------------------------------------------------- | ----------------- |
| `DATASTORE`               | Yes      | Datastore name, set to `opensearch`                      |                   |
| `BEARER_TOKEN`            | Yes      | Secret token                                             |                   |
| `OPENAI_API_KEY`          | Yes      | OpenAI API key                                           |                   |
| `OS_ENDPOINT`             | Yes      | Alibaba Cloud OpenSearch instance endpoint address       |                   |
| `OS_INSTANCE_ID`          | Yes      | Alibaba Cloud OpenSearch instance instance id            |                   |
| `OS_TABLE_NAME`           | Yes      | Alibaba Cloud OpenSearch instance table name             |                   |
| `OS_ACCESS_USER_NAME`     | Yes      | Alibaba Cloud OpenSearch instance access user name       |                   |
| `OS_ACCESS_PASS_WORD`     | Yes      | Alibaba Cloud OpenSearch instance access password        |                   |
| `OS_EMBEDDING_INDEX_NAME` | YES      | Alibaba Cloud OpenSearch instance embedding index name   |                   |


**Field Name Mapping Environment Variables:**

| Name                     | Required | Description                         | Default           |
| ------------------------ | -------- | ----------------------------------- | ----------------- |
| `OS_FIELDS_ID`           | No       | the name of id filed                |`id`               |
| `OS_FIELDS_TEXT`         | No       | the name of text filed              |`text`             |
| `OS_FIELDS_EMBEDDING`    | No       | the name of embedding filed         |`embedding`        |
| `OS_FIELDS_DOCUMENT_ID`  | No       | the name of document id filed       |`document_id`      |
| `OS_FIELDS_SOURCE`       | No       | the name of document source filed   |`document_id`      |
| `OS_FIELDS_SOURCE_ID`    | No       | the name of source id filed         |`source_id`        |
| `OS_FIELDS_URL`          | No       | the name of url filed               |`url`              |
| `OS_FIELDS_CREATED_AT`   | No       | the name of create at filed         |`create_at`        |
| `OS_FIELDS_AUTHOR`       | No       | the name of author filed            |`author`           |


## Running OpenSearch Integration Tests

A suite of integration tests verifies the OpenSearch integration. Launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/alibabacloudopensearch/test_alibabacloud_opensearch_datastore.py
```

If you encounter any problems during use, please feel free to contact [xingshaomin.xsm@alibaba-inc.com](xingshaomin.xsm@alibaba-inc.com) , and we will do our best to provide you with assistance and support.