# Hippo

## Deploying the Database

You can deploy and manage Hippo using hippo cloud Follow the instructions [here](http://hippo.transwarp.io/) to get started.

**Environment Variables:**

| Name                       | Required | Description                                                                                                                                  |
|----------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------|
| `DATASTORE`                | Yes      | Datastore name, set to `hippo`                                                                                                               |
| `BEARER_TOKEN`             | Yes      | Your bearer token                                                                                                                            |
| `OPENAI_API_KEY`           | Yes      | Your OpenAI API key                                                                                                                          |
| `HIPPO_DATABASE`           | Optional | Hippo database name, defaults to default                                                                                                     
| `HIPPO_TABLE`              | Yes      | Hippo table name, defaults to a random UUID                                                                                                  |
| `HIPPO_HOST`               | Yes      | Hippo host IP,                                                                                                                               |
| `HIPPO_PORT`               | Yes      | Hippo port,                                                                                                                                  |
| `HIPPO_USER`               | Optional | Hippo username if RBAC is enabled, defaults to `shiva`                                                                                       |
| `HIPPO_PASSWORD`           | Optional | Hippo password if required, defaults to `shiva`                                                                                               |
