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

| Name             | Required | Description                                                                          |
| ---------------- | -------- |--------------------------------------------------------------------------------------|
| `DATASTORE`      | Yes      | Datastore name. Set this to `weaviate`                                               |
| `BEARER_TOKEN`   | Yes      | Your [secret token](/README.md#general-environment-variables) (not the Weaviate one) |
| `OPENAI_API_KEY` | Yes      | Your OpenAI API key                                                                  |

**Weaviate Datastore Environment Variables**

| Name             | Required | Description                                                        | Default            |
|------------------| -------- | ------------------------------------------------------------------ | ------------------ |
| `WEAVIATE_URL`  | Optional | Your weaviate instance's url/WCS endpoint              | `http://localhost:8080` |           |
| `WEAVIATE_CLASS` | Optional | Your chosen Weaviate class/collection name to store your documents | OpenAIDocument     |

**Weaviate Auth Environment Variables**

If using WCS instances, set the following environment variables:

| Name                | Required | Description                    |
| ------------------- | -------- | ------------------------------ |
| `WEAVIATE_API_KEY` | Yes      | Your API key WCS      |

Learn more about accessing your [WCS API key](https://weaviate.io/developers/wcs/guides/authentication#access-api-keys).