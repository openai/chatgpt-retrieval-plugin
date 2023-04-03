# Weaviate

## Set up a Weaviate Instance

[Weaviate](https://weaviate.io/) is an open-source vector search engine designed to scale seamlessly into billions of data objects. This implementation supports hybrid search out-of-the-box (meaning it will perform better for keyword searches).

You can run Weaviate in 4 ways:

- **SaaS** – with [Weaviate Cloud Services (WCS)](https://weaviate.io/pricing).

  WCS is a fully managed service that takes care of hosting, scaling, and updating your Weaviate instance. You can try it out for free with a sandbox that lasts for 30 days.

  To set up a SaaS Weaviate instance with WCS:

  1.  Navigate to [Weaviate Cloud Console](https://console.weaviate.io/).
  2.  Register or sign in to your WCS account.
  3.  Create a new cluster with the following settings:
      - `Name` – a unique name for your cluster. The name will become part of the URL used to access this instance.
      - `Subscription Tier` – Sandbox for a free trial, or contact [hello@weaviate.io](mailto:hello@weaviate.io) for other options.
      - `Weaviate Version` - The latest version by default.
      - `OIDC Authentication` – Enabled by default. This requires a username and password to access your instance.
  4.  Wait for a few minutes until your cluster is ready. You will see a green tick ✔️ when it's done. Copy your cluster URL.

- **Hybrid SaaS**

  > If you need to keep your data on-premise for security or compliance reasons, Weaviate also offers a Hybrid SaaS option: Weaviate runs within your cloud instances, but the cluster is managed remotely by Weaviate. This gives you the benefits of a managed service without sending data to an external party.

  The Weaviate Hybrid SaaS is a custom solution. If you are interested in this option, please reach out to [hello@weaviate.io](mailto:hello@weaviate.io).

- **Self-hosted** – with a Docker container

  To set up a Weaviate instance with Docker:

  1. [Install Docker](https://docs.docker.com/engine/install/) on your local machine if it is not already installed.
  2. [Install the Docker Compose Plugin](https://docs.docker.com/compose/install/)
  3. Download a `docker-compose.yml` file with this `curl` command:

     ```
     curl -o docker-compose.yml "https://configuration.weaviate.io/v2/docker-compose/docker-compose.yml?modules=standalone&runtime=docker-compose&weaviate_version=v1.18.0"
     ```

     Alternatively, you can use Weaviate's docker compose [configuration tool](https://weaviate.io/developers/weaviate/installation/docker-compose) to generate your own `docker-compose.yml` file.

  4. Run `docker compose up -d` to spin up a Weaviate instance.

     > To shut it down, run `docker compose down`.

- **Self-hosted** – with a Kubernetes cluster

  To configure a self-hosted instance with Kubernetes, follow Weaviate's [documentation](https://weaviate.io/developers/weaviate/installation/kubernetes).

## Configure Weaviate Environment Variables

You need to set some environment variables to connect to your Weaviate instance.

**Retrieval App Environment Variables**

| Name             | Required | Description                            |
| ---------------- | -------- | -------------------------------------- |
| `DATASTORE`      | Yes      | Datastore name. Set this to `weaviate` |
| `BEARER_TOKEN`   | Yes      | Your secret token                      |
| `OPENAI_API_KEY` | Yes      | Your OpenAI API key                    |

**Weaviate Datastore Environment Variables**

| Name             | Required | Description                                                        | Default            |
| ---------------- | -------- | ------------------------------------------------------------------ | ------------------ |
| `WEAVIATE_HOST`  | Optional | Your Weaviate instance host address (see notes below)              | `http://127.0.0.1` |
| `WEAVIATE_PORT`  | Optional | Your Weaviate port number                                          | 8080               |
| `WEAVIATE_INDEX` | Optional | Your chosen Weaviate class/collection name to store your documents | OpenAIDocument     |

> For **WCS instances**, set `WEAVIATE_PORT` to 443 and `WEAVIATE_HOST` to `https://(wcs-instance-name).weaviate.network`. For example: `https://my-project.weaviate.network/`.

> For **self-hosted instances**, if your instance is not at 127.0.0.1:8080, set `WEAVIATE_HOST` and `WEAVIATE_PORT` accordingly. For example: `WEAVIATE_HOST=http://localhost/` and `WEAVIATE_PORT=4040`.

**Weaviate Auth Environment Variables**

If you enabled OIDC authentication for your Weaviate instance (recommended for WCS instances), set the following environment variables. If you enabled anonymous access, skip this section.

| Name                | Required | Description                    |
| ------------------- | -------- | ------------------------------ |
| `WEAVIATE_USERNAME` | Yes      | Your OIDC or WCS username      |
| `WEAVIATE_PASSWORD` | Yes      | Your OIDC or WCS password      |
| `WEAVIATE_SCOPES`   | Optional | Space-separated list of scopes |

Learn more about [authentication in Weaviate](https://weaviate.io/developers/weaviate/configuration/authentication#overview) and the [Python client authentication](https://weaviate-python-client.readthedocs.io/en/stable/weaviate.auth.html).

**Weaviate Batch Import Environment Variables**

Weaviate uses a batching mechanism to perform operations in bulk. This makes importing and updating your data faster and more efficient. You can adjust the batch settings with these optional environment variables:

| Name                             | Required | Description                                                  | Default |
| -------------------------------- | -------- | ------------------------------------------------------------ | ------- |
| `WEAVIATE_BATCH_SIZE`            | Optional | Number of insert/updates per batch operation                 | 20      |
| `WEAVIATE_BATCH_DYNAMIC`         | Optional | Lets the batch process decide the batch size                 | False   |
| `WEAVIATE_BATCH_TIMEOUT_RETRIES` | Optional | Number of retry-on-timeout attempts                          | 3       |
| `WEAVIATE_BATCH_NUM_WORKERS`     | Optional | The max number of concurrent threads to run batch operations | 1       |

> **Note:** The optimal `WEAVIATE_BATCH_SIZE` depends on the available resources (RAM, CPU). A higher value means faster bulk operations, but also higher demand for RAM and CPU. If you experience failures during the import process, reduce the batch size.

> Setting `WEAVIATE_BATCH_SIZE` to `None` means no limit to the batch size. All insert or update operations would be sent to Weaviate in a single operation. This might be risky, as you lose control over the batch size.

Learn more about [batch configuration in Weaviate](https://weaviate.io/developers/weaviate/client-libraries/python#batch-configuration).
