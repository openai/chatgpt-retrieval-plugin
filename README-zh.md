# ChatGPT 检索插件

> **点击[此处](https://openai.com/waitlist/plugins)加入 ChatGPT 插件等待名单！**

在[这里](https://cdn.openai.com/chat-plugins/retrieval-gh-repo-readme/Retrieval-Final.mp4)可以找到一个示例视频，其中检索插件可以访问从 2018 年到 2022 年的联合国年度报告。

## 介绍

ChatGPT 检索插件存储库提供了一种使用自然语言查询对个人或组织文档进行语义搜索和检索的灵活解决方案。存储库分为几个目录：

| 目录                          | 描述                                                                                                            |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| [`datastore`](/datastore)     | 包含使用各种向量数据库提供程序存储和查询文档嵌入的核心逻辑。                                                  |
| [`examples`](/examples)       | 包括示例配置、身份验证方法和特定于提供程序的示例。                                                               |
| [`models`](/models)           | 包含插件使用的数据模型，如文档和元数据模型。                                                                     |
| [`scripts`](/scripts)         | 提供用于从不同的数据源处理和上传文档的脚本。                                                                    |
| [`server`](/server)           | 存储主要的 FastAPI 服务器实现。                                                                                  |
| [`services`](/services)       | 包含用于任务（如分块、元数据提取和 PII 检测）的实用程序服务。                                                   |
| [`tests`](/tests)             | 包括各种向量数据库提供程序的集成测试。                                                                            |
| [`.well-known`](/.well-known) | 存储插件清单文件和 OpenAPI 模式，这些定义了插件配置和 API 规范。                                              |

本 README 提供了有关如何设置、开发和部署 ChatGPT 检索插件的详细信息。

## 目录

- [关于](#about)
    - [插件](#plugins)
    - [检索插件](#retrieval-plugin)
    - [记忆功能](#memory-feature)
    - [安全性](#security)
    - [API 端点](#api-endpoints)
- [快速入门](#quickstart)
- [开发](#development)
    - [设置](#setup)
        - [通用环境变量](#general-environment-variables)
    - [选择向量数据库](#choosing-a-vector-database)
        - [Pinecone](#pinecone)
        - [Weaviate](#weaviate)
        - [Zilliz](#zilliz)
        - [Milvus](#milvus)
        - [Qdrant](#qdrant)
        - [Redis](#redis)
    - [本地运行 API](#running-the-api-locally)
    - [个性化](#personalization)
    - [身份验证方法](#authentication-methods)
- [部署](#deployment)
    - [部署到 Fly.io](#deploying-to-flyio)
    - [部署到 Heroku](#deploying-to-heroku)
    - [其他部署选项](#other-deployment-options)
- [Webhooks](#webhooks)
- [脚本](#scripts)
- [限制](#limitations)
- [贡献者](#contributors)
- [未来方向](#future-directions)

## about

### plugins

插件是专门为 ChatGPT 等语言模型设计的聊天扩展，使它们能够访问最新的信息、运行计算或与第三方服务进行交互以响应用户的请求。 它们解锁了广泛的潜在用例，并增强了语言模型的能力。

开发人员可以通过网站公开 API 并提供一个描述 API 的标准化清单文件来创建插件。ChatGPT 会消费这些文件，并允许 AI 模型调用开发人员定义的 API。

插件包含以下内容：

- 一个 API
- 一个 API 模式（OpenAPI JSON 或 YAML 格式）
- 定义插件相关元数据的清单文件（JSON 文件）

检索插件已经包含了所有这些组件。请在[这里](https://openai.com/blog/chatgpt-plugins)阅读 Chat Plugins 的博客文章，并在[这里](https://platform.openai.com/docs/plugins/introduction)找到文档。

### retrieval-plugin

这是 ChatGPT 的一个插件，它可以对个人或组织文档进行语义搜索和检索。它允许用户通过自然语言询问或表达需求，从数据源（如文件、笔记或电子邮件）中获取最相关的文档片段。企业可以使用此插件通过 ChatGPT 使其内部文档对员工可用。

该插件使用 OpenAI 的 `text-embedding-ada-002` 嵌入模型生成文档块的嵌入，然后使用后端的向量数据库存储和查询它们。作为一种开源和自托管的解决方案，开发人员可以部署自己的检索插件并将其注册到 ChatGPT 上。检索插件支持多个向量数据库提供程序，允许开发人员从列表中选择他们偏好的数据库提供程序。

FastAPI 服务器公开了插件的端点，用于插入、查询和删除文档。用户可以使用来源、日期、作者或其他标准的元数据过滤器来细化其搜索结果。该插件可以托管在任何支持 Docker 容器的云平台上，例如 Fly.io、Heroku 或 Azure 容器应用程序。为了使向量数据库始终更新到最新的文档，插件可以持续地从各种数据源处理和存储文档，使用传入的 Webhooks 到插入和删除端点。工具如 [Zapier](https://zapier.com) 或 [Make](https://www.make.com) 可以帮助基于事件或计划配置 Webhooks。

### memory-feature

检索插件的一个显著特点是它可以为 ChatGPT 提供记忆功能。通过利用插件的插入端点，ChatGPT 可以将对话片段保存到向量数据库中以供以后参考（仅在用户提示时才这样做）。这个功能可以使 ChatGPT 能够记住和检索以前对话中的信息，从而为更具上下文感知的聊天体验做出贡献。了解如何配置带有记忆功能的检索插件[here](/examples/memory)。

### security

检索插件允许 ChatGPT 搜索内容的向量数据库，并将最佳结果添加到 ChatGPT 会话中。这意味着它没有任何外部影响，主要的风险考虑是数据授权和隐私。开发人员应该只向其检索插件添加他们已经授权的内容，并且他们对出现在用户 ChatGPT 会话中没有任何问题。您可以从多种不同的身份验证方法中选择以保护插件（更多信息请参见[此处](#authentication-methods)）。

### api-endpoints

检索插件使用 Python 的 FastAPI 构建，它是一个用于构建 API 的 Web 框架。FastAPI 允许轻松开发、验证和文档化 API 端点。可以在[此处](https://fastapi.tiangolo.com/)找到 FastAPI 的文档。

使用 FastAPI 的好处之一是自动生成具有 Swagger UI 交互式 API 文档。当 API 在本地运行时，可以使用`<local_host_url，例如 http://0.0.0.0:8000>/docs`与 API 端点交互、测试其功能并查看预期的请求和响应模型。

插件公开以下端点，用于向向量数据库中插入、查询和删除文档。所有请求和响应都是 JSON 格式，并需要一个有效的 Bearer 令牌作为授权标头。

- `/upsert`: 此端点允许上传一个或多个文档，并将其文本和元数据存储在向量数据库中。将文档分成大约 200 个标记的块，每个块具有唯一的 ID。端点期望请求体中的文档列表，每个文档都有一个 `text` 字段和可选的 `id` 和 `metadata` 字段。`metadata` 字段可以包含以下可选子字段：`source`、`source_id`、`url`、`created_at` 和 `author`。端点返回插入的文档 ID 列表（如果未提供 ID，则会生成 ID）。

- `/upsert-file`: 此端点允许上传单个文件（PDF、TXT、DOCX、PPTX 或 MD）并将其文本和元数据存储在向量数据库中。文件将转换为纯文本并分成大约 200 个标记的块，每个块具有唯一的 ID。端点返回包含已插入文件的生成 ID 的列表。

- `/query`: 此端点允许使用一个或多个自然语言查询和可选的元数据过滤器查询向量数据库。端点期望请求体中的查询列表，每个查询都有一个 `query` 和可选的 `filter` 和 `top_k` 字段。`filter` 字段应包含以下子字段的子集：`source`、`source_id`、`document_id`、`url`、`created_at` 和 `author`。`top_k` 字段指定要为给定查询返回多少结果，默认值为 3。端点返回一个包含对象列表的列表，每个对象都包含给定查询的最相关文档块的列表，以及它们的文本、元数据和相似度分数。

- `/delete`: 此端点允许通过 ID、元数据筛选器或 delete_all 标志从向量数据库中删除一个或多个文档。请求正文中至少应包含以下参数之一：`ids`、`filter` 或 `delete_all`。`ids` 参数应是要删除的文档 ID 列表；将删除具有这些 ID 的文档的所有文档块。`filter` 参数应包含以下子字段的子集：`source`、`source_id`、`document_id`、`url`、`created_at` 和 `author`。`delete_all` 参数应是一个布尔值，表示是否删除向量数据库中的所有文档。该端点返回一个布尔值，指示删除是否成功。

可以通过在本地运行应用程序并导航到 http://0.0.0.0:8000/openapi.json 或在 OpenAPI 模式 [here](/.well-known/openapi.yaml) 中查找请求和响应模型的详细规范和示例。请注意，OpenAPI 模式仅包含 `/query` 端点，因为这是 ChatGPT 需要访问的唯一功能。这样，ChatGPT 可以仅使用插件基于自然语言查询或需求检索相关文档。但是，如果开发人员希望让 ChatGPT 也能记住以后的信息，他们可以使用 `/upsert` 端点将对话中的片段保存到向量数据库中。可以在 [这里](/examples/memory) 找到赋予 ChatGPT 访问 `/upsert` 端点的清单和 OpenAPI 模式的示例。

要包括自定义元数据字段，请编辑 `DocumentMetadata` 和 `DocumentMetadataFilter` 数据模型 [here](/models/models.py)，并更新 OpenAPI 模式 [here](/.well-known/openapi.yaml)。可以通过在本地运行应用程序、复制在 http://0.0.0.0:8000/sub/openapi.json 中找到的 JSON 并使用 [Swagger Editor](https://editor.swagger.io/) 将其转换为 YAML 格式来轻松更新此内容。或者，您可以替换 `openapi.yaml` 文件为 `openapi.json` 文件。

## quickstart

按照以下步骤快速设置和运行 ChatGPT 检索插件：

1. 如果尚未安装，请安装 Python 3.10。
2. 克隆存储库：`git clone https://github.com/openai/chatgpt-retrieval-plugin.git`
3. 导航到克隆的存储库目录：`cd /path/to/chatgpt-retrieval-plugin`
4. 安装 poetry：`pip install poetry`
5. 使用 Python 3.10 创建新的虚拟环境：`poetry env use python3.10`
6. 激活虚拟环境：`poetry shell`
7. 安装应用程序依赖项：`poetry install`
8. 设置所需的环境变量：

   ```
   export DATASTORE=<your_datastore>
   export BEARER_TOKEN=<your_bearer_token>
   export OPENAI_API_KEY=<your_openai_api_key>
   <Add the environment variables for your chosen vector DB here>
   ```

9. 在本地运行 API：`poetry run start`
10. 在 `http://0.0.0.0:8000/docs` 访问 API 文档，并测试 API 端点（确保添加您的 bearer token）。

有关设置、开发和部署 ChatGPT 检索插件的更详细信息，请参阅下面的完整开发部分。

## Development

### Setup

本应用程序使用Python 3.10，以及用于依赖管理的 [poetry](https://python-poetry.org/) 工具。

如果您的计算机上尚未安装Python 3.10，请先安装它。您可以从官方的[Python网站](https://www.python.org/downloads/)上下载Python 3.10，或使用包管理器，如 `brew` 或 `apt`，具体取决于您的系统。

Clone the repository from GitHub:

```
git clone https://github.com/openai/chatgpt-retrieval-plugin.git
```

Navigate to the cloned repository directory:

```
cd /path/to/chatgpt-retrieval-plugin
```

Install poetry:

```
pip install poetry
```

Create a new virtual environment that uses Python 3.10:

```
poetry env use python3.10
poetry shell
```

Install app dependencies using poetry:

```
poetry install
```

**Note:** If adding dependencies in the `pyproject.toml`, make sure to run `poetry lock` and `poetry install`.

#### General Environment Variables

API 需要以下环境变量才能正常工作:

| 名称 | 必填 | 描述 |
| ---- | ---- | ---- |
| `DATASTORE` | 是 | 这指定了您要使用的矢量数据库提供程序来存储和查询嵌入。您可以从`pinecone`，`weaviate`，`zilliz`，`milvus`，`qdrant`或`redis`中进行选择。 |
| `BEARER_TOKEN` | 是 | 这是一个机密令牌，您需要用它来认证您对 API 的请求。您可以使用任何工具或方法来生成令牌，例如 [jwt.io](https://jwt.io/)。 |
| `OPENAI_API_KEY` | 是 | 这是您的 OpenAI API 密钥，您需要使用 `text-embedding-ada-002` 模型生成嵌入。您可以通过在 [OpenAI](https://openai.com/) 上创建帐户来获得 API 密钥。 |

### Choosing a Vector Database

该插件支持多个向量数据库提供者，每个提供者都具有不同的功能、性能和定价。根据您选择的提供者，您需要使用不同的 Dockerfile 并设置不同的环境变量。以下各节提供有关使用每个向量数据库提供者的详细信息和说明。

#### Pinecone

[Pinecone](https://www.pinecone.io) 是一个专为速度、规模和更快上线而构建的托管矢量数据库。要将 Pinecone 用作矢量数据库提供程序，首先需要通过[注册账户](https://app.pinecone.io/)来获取 API 密钥。您可以从仪表板侧栏的“API Keys”部分访问您的 API 密钥。

当您第一次运行应用程序时，它将自动为您创建一个 Pinecone 索引。只需选择一个索引名称并将其设置为环境变量即可。

环境变量：

| 名称                   | 是否必需 | 描述                                                                                                                             |
| ---------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `DATASTORE`            | 是       | Datastore 名称，将其设置为 `pinecone`                                                                                            |
| `BEARER_TOKEN`         | 是       | 用于对 API 进行身份验证的密钥                                                                                                     |
| `OPENAI_API_KEY`       | 是       | 用于使用 `text-embedding-ada-002` 模型生成嵌入的 OpenAI API 密钥                                                               |
| `PINECONE_API_KEY`     | 是       | 您的 Pinecone API 密钥，在[Pinecone 控制台](https://app.pinecone.io/)中找到                                                    |
| `PINECONE_ENVIRONMENT` | 是       | 您的 Pinecone 环境，在 [Pinecone 控制台](https://app.pinecone.io/)中找到，例如 `us-west1-gcp`、`us-east-1-aws` 等           |
| `PINECONE_INDEX`       | 是       | 您选择的 Pinecone 索引名称。**注意：** 索引名称必须由小写字母、数字字符或 "-" 组成。                                 |

如果您想使用自定义配置创建自己的索引，可以使用 Pinecone SDK、API 或 Web 界面（[请参阅文档](https://docs.pinecone.io/docs/manage-indexes)）。请确保对嵌入使用 1536 的维度，并避免在元数据的文本字段上进行索引，因为这会显著降低性能。

```python
# Creating index with Pinecone SDK - use only if you wish to create the index manually.

import os, pinecone

pinecone.init(api_key=os.environ['PINECONE_API_KEY'],
              environment=os.environ['PINECONE_ENVIRONMENT'])

pinecone.create_index(name=os.environ['PINECONE_INDEX'],
                      dimension=1536,
                      metric='cosine',
                      metadata_config={
                          "indexed": ['source', 'source_id', 'url', 'created_at', 'author', 'document_id']})
```

#### Weaviate

##### 设置 Weaviate 实例

Weaviate 是一款开源矢量搜索引擎，旨在无缝扩展到数十亿个数据对象。此实现支持混合搜索（意味着它对关键字搜索的表现更好）。

您可以以 4 种方式运行 Weaviate：

- **SaaS** - 使用 [Weaviate Cloud Services（WCS）](https://weaviate.io/pricing)。

  WCS 是一个完全托管的服务，负责托管、扩展和更新您的 Weaviate 实例。您可以使用持续 30 天的沙箱免费试用。

  要使用 WCS 设置 SaaS Weaviate 实例：

    1. 导航到[Weaviate Cloud Console](https://console.weaviate.io/)。
    2. 注册或登录到您的 WCS 账户。
    3. 使用以下设置创建一个新集群：
        - `Name` - 您集群的唯一名称。该名称将成为访问此实例所使用的 URL 的一部分。
        - `Subscription Tier` - 免费试用沙箱，或联系 [hello@weaviate.io](mailto:hello@weaviate.io) 了解其他选项。
        - `Weaviate Version` - 默认为最新版本。
        - `OIDC Authentication` - 默认启用。这需要用户名和密码才能访问您的实例。
    4. 等待几分钟，直到您的集群准备就绪。完成后，您将看到绿色的勾 ✔️。复制您的集群 URL。

- **混合 SaaS**

  > 如果由于安全或合规原因需要将数据保存在本地，Weaviate 还提供了混合 SaaS 选项：Weaviate 在您的云实例中运行，但是集群由 Weaviate 远程管理。这为您提供了托管服务的好处，而不会将数据发送给外部方。

  Weaviate 混合 SaaS 是一种定制解决方案。如果您有兴趣使用此选项，请联系 [hello@weaviate.io](mailto:hello@weaviate.io)。

- **自托管** - 使用 Docker 容器

  要使用 Docker 设置 Weaviate 实例：

    1. 使用以下 `curl` 命令下载包含 `docker-compose.yml` 文件：

       ```
       curl -o docker-compose.yml "https://configuration.weaviate.io/v2/docker-compose/docker-compose.yml?modules=standalone&runtime=docker-compose&weaviate_version=v1.18.0"
       ```

       或者，您可以使用 Weaviate 的 Docker Compose [配置工具](https://weaviate.io/developers/weaviate/installation/docker-compose)来生成自己的 `docker-compose.yml` 文件。

    2. 运行 `docker-compose up -d` 启动 Weaviate 实例。

       > 要关闭它，请运行 `docker-compose down`。

- **自托管** - 使用 Kubernetes 集群

  要使用 Kubernetes 配置自托管实例，请按照 Weaviate 的[文档](https://weaviate.io/developers/weaviate/installation/kubernetes)进行操作。

##### 配置 Weaviate 环境变量

您需要设置一些环境变量以连接到 Weaviate 实例。

**Retrieval App 环境变量**

| 名称            | 是否必需 | 描述                          |
| --------------- | -------- | ----------------------------- |
| `DATASTORE`     | 是       | Datastore 名称。将其设置为 `weaviate` |
| `BEARER_TOKEN`  | 是       | 您的秘密令牌                    |
| `OPENAI_API_KEY`| 是       | 您的 OpenAI API 密钥            |

**Weaviate Datastore 环境变量**

| 名称            | 是否必需 | 描述                                          | 默认值            |
| --------------- | -------- | --------------------------------------------- | ------------------ |
| `WEAVIATE_HOST` | 可选      | 您的 Weaviate 实例主机地址（见下面的注释）    | `http://127.0.0.1` |
| `WEAVIATE_PORT` | 可选      | 您的 Weaviate 端口号                           | 8080               |
| `WEAVIATE_INDEX`| 可选      | 您选择的 Weaviate 类/集合名称来存储文档       | OpenAIDocument     |

> 对于 WCS 实例，请将 `WEAVIATE_PORT` 设置为 443，将 `WEAVIATE_HOST` 设置为 `https://(wcs-instance-name).weaviate.network`。例如：`https://my-project.weaviate.network/`。

> 对于自托管实例，如果您的实例不在 127.0.0.1:8080 上，请相应地设置 `WEAVIATE_HOST` 和 `WEAVIATE_PORT`。例如：`WEAVIATE_HOST=http://localhost/` 和 `WEAVIATE_PORT=4040`。

**Weaviate 认证环境变量**

如果您为 Weaviate 实例启用了 OIDC 认证（推荐用于 WCS 实例），请设置以下环境变量。如果您启用了匿名访问，请跳过此部分。

| 名称                 | 是否必需 | 描述                          |
| -------------------- | -------- | ----------------------------- |
| `WEAVIATE_USERNAME`  | 是       | 您的 OIDC 或 WCS 用户名        |
| `WEAVIATE_PASSWORD`  | 是       | 您的 OIDC 或 WCS 密码        |
| `WEAVIATE_SCOPES`    | 可选      | 空格分隔的范围列表 |

了解更多关于[Weaviate 认证](https://weaviate.io/developers/weaviate/configuration/authentication#overview)和[Python 客户端认证](https://weaviate-python-client.readthedocs.io/en/stable/weaviate.auth.html)的信息。

**Weaviate 批量导入环境变量**

Weaviate 使用批处理机制批量执行操作。这使得导入和更新数据更快、更高效。您可以使用以下可选的环境变量来调整批处理设置：

| 名称                             | 是否必需 | 描述                                                  | 默认值 |
| -------------------------------- | -------- | ------------------------------------------------------------ | ------- |
| `WEAVIATE_BATCH_SIZE`            | 可选      | 每批次操作的插入/更新数量 | 20      |
| `WEAVIATE_BATCH_DYNAMIC`         | 可选      | 让批处理过程决定批量大小                 | False   |
| `WEAVIATE_BATCH_TIMEOUT_RETRIES` | 可选      | 超时重试尝试次数                          | 3       |
| `WEAVIATE_BATCH_NUM_WORKERS`     | 可选      | 最大并发线程数，用于运行批处理操作       | 1       |

> **注意：**最佳的 `WEAVIATE_BATCH_SIZE` 取决于可用资源（RAM、CPU）。较高的值意味着更快的批量操作，但也意味着对 RAM 和 CPU 的需求更高。如果在导入过程中遇到故障，请减小批处理大小。

> 将 `WEAVIATE_BATCH_SIZE` 设置为 `None` 表示批处理大小无限制。所有插入或更新操作都将一次性发送到 Weaviate 中。这可能是有风险的，因为您失去了对批处理大小的控制。

了解更多关于[Weaviate 批处理配置](https://weaviate.io/developers/weaviate/client-libraries/python#batch-configuration)的信息。

#### Zilliz

Zilliz 是一个专为亿级规模设计的托管的云原生向量数据库。Zilliz 提供了许多关键功能，例如：

- 多种索引算法
- 多个距离度量
- 标量过滤
- 时间旅行搜索
- 回滚和快照
- 完整的 RBAC
- 99.9% 的正常运行时间
- 分离的存储和计算
- 多语言 SDK

在[这里](https://zilliz.com)找到更多信息。

**自托管 vs SaaS**

Zilliz 是一款 SaaS 数据库，但提供了开源解决方案 Milvus。两个选项都可以在亿级规模下进行快速搜索，但是 Zilliz 为您处理数据管理。它会自动缩放计算和存储资源，并为您的数据创建最佳索引。在[这里](https://zilliz.com/doc/about_zilliz_cloud)查看比较。

##### 部署数据库

Zilliz Cloud 可以通过几个简单的步骤进行部署。首先，[在此处](https://cloud.zilliz.com/signup)创建一个账户。一旦您设置好了账户，请按照[此处](https://zilliz.com/doc/quick_start)的指南设置数据库并获取所需的参数。

环境变量：

| 名称                 | 必需   | 描述                                       |
| ------------------- | ------ | ------------------------------------------ |
| `DATASTORE`         | 是     | Datastore 名称，设置为 `zilliz`            |
| `BEARER_TOKEN`      | 是     | 您的秘密令牌                               |
| `OPENAI_API_KEY`    | 是     | 您的 OpenAI API 密钥                       |
| `ZILLIZ_COLLECTION` | 可选   | Zilliz 集合名称，默认为随机 UUID           |
| `ZILLIZ_URI`        | 是     | Zilliz 实例的 URI                           |
| `ZILLIZ_USER`       | 是     | Zilliz 用户名                              |
| `ZILLIZ_PASSWORD`   | 是     | Zilliz 密码                                |

#### 运行 Zilliz 集成测试

提供了一套集成测试，用于验证 Zilliz 集成。要运行测试，需要创建一个 Zilliz 数据库并更新环境变量。

然后，使用以下命令启动测试套件：

```bash
pytest ./tests/datastore/providers/zilliz/test_zilliz_datastore.py
```

#### Milvus

Milvus 是一款开源的、云原生的矢量数据库，可扩展到数十亿个向量。它是 Zilliz 的开源版本。支持以下功能：

- 各种索引算法和距离度量
- 标量过滤和时间旅行搜索
- 回滚和快照
- 多语言 SDK
- 存储和计算分离
- 云扩展性
- 开发人员为先的社区，支持多种语言

请访问 [Github](https://github.com/milvus-io/milvus) 了解更多信息。

##### 部署数据库

你可以使用 Docker Compose、Helm、K8 的 Operator 或 Ansible 部署和管理 Milvus。请按照 [这里](https://milvus.io/docs) 的说明开始。

环境变量：

| 名称                | 必填   | 描述                                           |
| ------------------- | ------ | ---------------------------------------------- |
| `DATASTORE`         | Yes    | 数据存储名称，设置为 `milvus`                 |
| `BEARER_TOKEN`      | Yes    | 您的 Bearer Token                              |
| `OPENAI_API_KEY`    | Yes    | 您的 OpenAI API Key                            |
| `MILVUS_COLLECTION` | Optional | Milvus 集合名称，如果不指定则使用随机 UUID     |
| `MILVUS_HOST`       | Optional | Milvus 主机 IP 地址，如果不指定则默认为 `localhost` |
| `MILVUS_PORT`       | Optional | Milvus 端口号，如果不指定则默认为 `19530`         |
| `MILVUS_USER`       | Optional | 如果启用了 RBAC，则为 Milvus 用户名，否则默认为 `None` |
| `MILVUS_PASSWORD`   | Optional | 如果需要，为 Milvus 密码，默认为 `None`              |

#### 运行 Milvus 集成测试

可用一套集成测试来验证 Milvus 的集成。要运行测试，请在示例文件夹中运行 milvus docker compose。

然后，使用以下命令启动测试套件：

```bash
pytest ./tests/datastore/providers/milvus/test_milvus_datastore.py
```

#### Qdrant

Qdrant是一个可以存储文档和向量嵌入的向量数据库。它可以作为自托管版本或托管的[Qdrant Cloud](https://cloud.qdrant.io/)解决方案运行。两个选项的配置几乎相同，除了[Qdrant Cloud](https://cloud.qdrant.io/)提供的API密钥之外。

环境变量：

| 名称 | 必需 | 描述 | 默认值 |
| ------------------- | -------- | ----------------------------------------------------------- | ------------------ |
| `DATASTORE` | 是 | 数据存储名称，设置为`qdrant` | |
| `BEARER_TOKEN` | 是 | 秘密令牌 | |
| `OPENAI_API_KEY` | 是 | OpenAI API密钥 | |
| `QDRANT_URL` | 是 | Qdrant实例URL | `http://localhost` |
| `QDRANT_PORT` | 可选 | Qdrant HTTP通信的TCP端口 | `6333` |
| `QDRANT_GRPC_PORT` | 可选 | Qdrant GRPC通信的TCP端口 | `6334` |
| `QDRANT_API_KEY` | 可选 | [Qdrant Cloud](https://cloud.qdrant.io/)的Qdrant API密钥 | |
| `QDRANT_COLLECTION` | 可选 | Qdrant集合名称 | `document_chunks` |

##### Qdrant Cloud

对于托管的[Qdrant Cloud](https://cloud.qdrant.io/)版本，请提供Qdrant实例URL和[Qdrant Cloud UI](https://cloud.qdrant.io/)中的API密钥。

**示例:**

```bash
QDRANT_URL="https://YOUR-CLUSTER-URL.aws.cloud.qdrant.io"
QDRANT_API_KEY="<YOUR_QDRANT_CLOUD_CLUSTER_API_KEY>"
```

其他参数是可选的，如果需要可以更改。

##### 自托管的 Qdrant 实例

对于自托管的版本，请使用 Docker 容器或官方 Helm Chart 进行部署。唯一必需的参数是指向 Qdrant 服务器 URL 的 `QDRANT_URL`。

**示例:**

```bash
QDRANT_URL="http://YOUR_HOST.example.com:6333"
```

其他参数是可选的，如果需要可以更改。


##### 运行 Qdrant 集成测试

一套集成测试可用于验证 Qdrant 集成。要运行测试，请在 Docker 容器中启动本地 Qdrant 实例。

```bash
docker run -p "6333:6333" -p "6334:6334" qdrant/qdrant:v1.0.3
```

Then, launch the test suite with this command:

```bash
pytest ./tests/datastore/providers/test_qdrant_datastore.py
```

#### Redis

通过创建一个带有[Redis Stack docker 容器](/examples/docker/redis/docker-compose.yml)的 Redis 数据库，将 Redis 用作低延迟向量引擎。对于托管/托管解决方案，请尝试[Redis Cloud](https://app.redislabs.com/#/)。

- 数据库需要 RediSearch 模块（v 2.6 ++），该模块包含在自托管的 docker compose 中。
- 使用 Redis docker 镜像运行应用程序：在 [此目录](/examples/docker/redis/)中执行 `docker compose up -d`。
- 应用程序在第一次运行时自动创建 Redis 向量搜索索引。可以选择使用特定名称创建自定义索引，并将其设置为环境变量（见下文）。
- 要启用更多的混合搜索功能，请在[此处](/datastore/providers/redis_datastore.py)调整文档架构。

环境变量：

| 名称                    | 必需 | 描述                                                                                             | 默认值       |
| ----------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------- | ----------- |
| `DATASTORE`             | 是 | 数据存储名称，设置为 `redis`                                                                               |             |
| `BEARER_TOKEN`          | 是 | 秘密令牌                                                                                                           |             |
| `OPENAI_API_KEY`        | 是 | OpenAI API密钥                                                                                                       |             |
| `REDIS_HOST`            | 可选 | Redis 主机URL                                                                                                       | `localhost` |
| `REDIS_PORT`            | 可选 | Redis 端口                                                                                                           | `6379`      |
| `REDIS_PASSWORD`        | 可选 | Redis 密码                                                                                                           | 无密码      |
| `REDIS_INDEX_NAME`      | 可选 | Redis 向量索引名称                                                                                                  | `index`     |
| `REDIS_DOC_PREFIX`      | 可选 | 索引的 Redis 键前缀                                                                                                | `doc`       |
| `REDIS_DISTANCE_METRIC` | 可选 | 向量相似度距离度量                                                                                                 | `COSINE`    |
| `REDIS_INDEX_TYPE`      | 可选 | [向量索引算法类型](https://redis.io/docs/stack/search/reference/vectors/#creation-attributes-per-algorithm) | `FLAT`      |

### Running the API locally

要在本地运行 API，首先需要使用 `export` 命令设置必要的环境变量：

```
export DATASTORE=<your_datastore>
export BEARER_TOKEN=<your_bearer_token>
export OPENAI_API_KEY=<your_openai_api_key>
<Add the environment variables for your chosen vector DB here>
```

使用以下命令启动 API：

```
poetry run start
```

在终端中显示的 URL 后附加 `docs`，在浏览器中打开它以访问 API 文档并尝试使用端点（例如，http://0.0.0.0:8000/docs）。确保输入您的 Bearer Token 并测试 API 端点。

**注意：**如果您在 pyproject.toml 文件中添加了新的依赖项，则需要运行 `poetry lock` 和 `poetry install` 更新锁文件并安装新的依赖项。

### personalization

您可以通过以下方法为自己的用例个性化检索插件：

- **替换标志**: 用您自己的标志替换 [logo.png](/.well-known/logo.png) 中的图像。

- **编辑数据模型**: 在 [models.py](/models/models.py) 中编辑 `DocumentMetadata` 和 `DocumentMetadataFilter` 数据模型，以添加自定义元数据字段。相应地更新 [openapi.yaml](/.well-known/openapi.yaml) 中的 OpenAPI 模式。为了更轻松地更新 OpenAPI 模式，您可以在本地运行应用程序，然后导航到 `http://0.0.0.0:8000/sub/openapi.json` 并复制网页的内容。然后进入 [Swagger Editor](https://editor.swagger.io/) 并粘贴 JSON 以将其转换为 YAML 格式。您还可以将 [.well-known](/.well-known) 文件夹中的 [openapi.yaml](/.well-known/openapi.yaml) 文件替换为 openapi.json 文件。

- **更改插件名称、说明和使用说明**: 更新模型的插件名称、用户界面说明和使用说明。您可以在 [main.py](/server/main.py) 文件中编辑说明，或者更新 [openapi.yaml](/.well-known/openapi.yaml) 文件。按照上一步的说明更新 OpenAPI 模式。

- **启用 ChatGPT 保存会话信息**: 请参阅 [memory example folder](/examples/memory) 中的说明。

### authentication-methods

您可以从四个选项中选择一种方法来验证对插件的请求：

1. **无验证**：任何人都可以添加您的插件并使用其 API，而无需任何凭据。如果您只公开不敏感或已公开的文档，则此选项适合您。它不提供数据安全性。如果使用此方法，请将此 [main.py](/examples/authentication-methods/no-auth/main.py) 的内容复制到 [actual main.py file](/server/main.py) 中。示例清单 [here](/examples/authentication-methods/no-auth/ai-plugin.json)。

2. **HTTP Bearer**：您可以使用一个密钥令牌作为头文件，以授权对插件的请求。此选项有两个变体：

    - **用户级别**（此实现的默认值）：将您的插件添加到 ChatGPT 的每个用户在添加插件时必须提供 bearer 令牌。您可以使用任何工具或方法（例如 [jwt.io](https://jwt.io/)）生成和分发这些令牌。此方法提供更好的安全性，因为每个用户都必须输入共享访问令牌。如果您需要为每个用户提供唯一的访问令牌，则需要在 [main.py](/server/main.py) 文件中自己实现此方法。示例清单 [here](/examples/authentication-methods/user-http/ai-plugin.json)。

    - **服务级别**：任何人都可以添加您的插件并使用其 API，而无需凭据，但您必须在注册插件时添加一个 bearer 令牌。安装插件时，您需要添加您的 bearer 令牌，然后将从 ChatGPT 接收一个令牌，您必须在托管的清单文件中包含该令牌。 ChatGPT 将使用您的令牌代表添加插件的所有用户授权对插件的请求。此方法对用户更加方便，但可能不太安全，因为所有用户共享相同的令牌，不需要在安装插件时添加令牌。示例清单 [here](/examples/authentication-methods/service-http/ai-plugin.json)。

3. **OAuth**：用户必须经过 OAuth 流程才能添加您的插件。您可以使用 OAuth 提供程序对添加您的插件的用户进行身份验证并授予他们访问您的 API 的权限。此方法提供了最高级别的安全性和控制，因为用户通过受信任的第三方提供程序进行身份验证。但是，您将需要在 [main.py](/server/main.py) 文件中自己实现 OAuth 流程，并在清单文件中提供必要的参数。示例清单 [here](/examples/authentication-methods/oauth/ai-plugin.json)。

在选择最适合您的用例和安全需求的认证方法之前，请考虑每种认证方法的优缺点。如果您选择使用与默认（用户级 HTTP）不同的方法，请确保更新清单文件[这里](/.well-known/ai-plugin.json)。

## Deployment

您可以根据自己的喜好和需求将应用程序部署到不同的云服务提供商。但是，无论您选择哪个提供商，都需要更新应用程序中的两个文件：[openapi.yaml](/.well-known/openapi.yaml) 和 [ai-plugin.json](/.well-known/ai-plugin.json)。如上所述，这些文件分别定义了您的应用程序的 API 规范和 AI 插件配置。您需要在这两个文件中更改 url 字段以匹配您部署的应用程序的地址。

在部署应用程序之前，您可能希望从 [pyproject.toml](/pyproject.toml) 文件中删除未使用的依赖项，以减少应用程序的大小并提高其性能。根据您选择的向量数据库提供商，可以删除不需要的软件包。

以下是每个向量数据库提供商可以删除的软件包：

- **Pinecone:** 删除 `weaviate-client`、`pymilvus`、`qdrant-client` 和 `redis`。
- **Weaviate:** 删除 `pinecone-client`、`pymilvus`、`qdrant-client` 和 `redis`。
- **Zilliz:** 删除 `pinecone-client`、`weaviate-client`、`qdrant-client` 和 `redis`。
- **Milvus:** 删除 `pinecone-client`、`weaviate-client`、`qdrant-client` 和 `redis`。
- **Qdrant:** 删除 `pinecone-client`、`weaviate-client`、`pymilvus` 和 `redis`。
- **Redis:** 删除 `pinecone-client`、`weaviate-client`、`pymilvus` 和 `qdrant-client`。

从 `pyproject.toml` 文件中删除不必要的软件包后，您无需手动运行 `poetry lock` 和 `poetry install`。提供的 Dockerfile 使用 `poetry export` 命令生成的 `requirements.txt` 文件来安装所需的依赖项。

部署应用程序后，可以使用其中一个[脚本](/scripts)上传一批初始文档，也可以调用 `/upsert` 端点，例如：

```bash
curl -X POST https://your-app-url.com/upsert \
  -H "Authorization: Bearer <your_bearer_token>" \
  -H "Content-type: application/json" \
  -d '{"documents": [{"id": "doc1", "text": "Hello world", "metadata": {"source_id": "12345", "source": "file"}}, {"text": "How are you?", "metadata": {"source_id": "23456"}}]}'
```

### 部署到 Fly.io

要将此存储库中的 Docker 容器部署到 Fly.io，请按照以下步骤操作：

如果您的本地机器尚未安装 Docker，请[安装 Docker](https://docs.docker.com/engine/install/)。

在本地机器上安装[Fly.io CLI](https://fly.io/docs/getting-started/installing-flyctl/)。

Clone the repository from GitHub:

```
git clone https://github.com/openai/chatgpt-retrieval-plugin.git
```

Navigate to the cloned repository directory:

```
cd path/to/chatgpt-retrieval-plugin
```

Log in to the Fly.io CLI:

```
flyctl auth login
```

Create and launch your Fly.io app:

```
flyctl launch
```

请按照终端中的说明进行操作：

- 选择您的应用程序名称
- 选择您的应用程序地区
- 不添加任何数据库
- 不要立即部署（如果您这样做，由于环境变量尚未设置，第一次部署可能会失败）

设置必要的环境变量:

```
flyctl secrets set DATASTORE=your_datastore \
OPENAI_API_KEY=your_openai_api_key \
BEARER_TOKEN=your_bearer_token \
<Add the environment variables for your chosen vector DB here>
```

或者，你可以在 [Fly.io 控制台](https://fly.io/dashboard) 中设置环境变量。

在这一步，你可以在你的插件清单文件 [这里](/.well-known/ai-plugin.json) 和你的 OpenAPI 模式 [这里](/.well-known/openapi.yaml) 中更改插件的 URL 为你 Fly.io 应用的 URL，这将是 `https://your-app-name.fly.dev`。

Deploy your app with:

```
flyctl deploy
```

完成这些步骤后，你的 Docker 容器应该已经部署到 Fly.io 并且已经设置好了必要的环境变量。你可以通过运行以下命令来查看你的应用程序：

```
flyctl open
```

它将打开你的应用程序 URL。你应该能够在 `<your_app_url>/.well-known/openapi.yaml` 找到 OpenAPI 模式，而插件清单文件位于 `<your_app_url>/.well-known/ai-plugin.json`。

要查看你的应用程序日志：

```
flyctl logs
```

现在，请确保你已经在你的插件清单文件 [这里](/.well-known/ai-plugin.json) 和你的 OpenAPI 模式 [这里](/.well-known/openapi.yaml) 中更改了插件的 URL，并使用 `flyctl deploy` 重新部署。该 URL 将为 `https://<your-app-name>.fly.dev`。

**调试提示：**
Fly.io 默认使用端口号 8080。

如果你的应用程序无法部署，请检查环境变量是否设置正确，然后检查你的端口是否配置正确。你也可以尝试使用 `flyctl launch` 命令的 [`-e` 标志](https://fly.io/docs/flyctl/launch/) 在启动时设置环境变量。

### 部署到 Heroku

要将此存储库中的 Docker 容器部署到 Heroku 并设置所需的环境变量，请按照以下步骤操作：

如果尚未安装，请在本地计算机上[安装 Docker](https://docs.docker.com/engine/install/)。

在本地计算机上安装 [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)。

Clone the repository from GitHub:

```
git clone https://github.com/openai/chatgpt-retrieval-plugin.git
```

Navigate to the cloned repository directory:

```
cd path/to/chatgpt-retrieval-plugin
```

Log in to the Heroku CLI:

```
heroku login
```

Create a Heroku app:

```
heroku create [app-name]
```

Log in to the Heroku Container Registry:

```
heroku container:login
```

Alternatively, you can use a command from the Makefile to log in to the Heroku Container Registry by running:

```
make heroku-login
```

Build the Docker image using the Dockerfile:

```
docker buildx build --platform linux/amd64 -t [image-name] .
```

(Replace `[image-name]` with the name you want to give your Docker image)

Push the Docker image to the Heroku Container Registry, and release the newly pushed image to your Heroku app.

```
docker tag [image-name] registry.heroku.com/[app-name]/web
docker push registry.heroku.com/[app-name]/web
heroku container:release web -a [app-name]
```

Alternatively, you can use a command from the to push the Docker image to the Heroku Container Registry by running:

```
make heroku-push
```

**注意：** 你需要编辑 Makefile 并使用你实际的应用程序名称替换 `<your app name>`。

为你的 Heroku 应用设置所需的环境变量：

```
heroku config:set DATASTORE=your_datastore \
OPENAI_API_KEY=your_openai_api_key \
BEARER_TOKEN=your_bearer_token \
<Add the environment variables for your chosen vector DB here> \
-a [app-name]
```

你也可以在 [Heroku 控制台](https://dashboard.heroku.com/apps) 中设置环境变量。

完成这些步骤后，你的 Docker 容器应该已经部署到 Heroku 并且已经设置好了必要的环境变量。你可以通过运行以下命令来查看你的应用程序：

```
heroku open -a [app-name]
```

它将打开你的应用程序 URL。你应该能够在 `<your_app_url>/.well-known/openapi.yaml` 找到 OpenAPI 模式，而插件清单文件位于 `<your_app_url>/.well-known/ai-plugin.json`。

要查看你的应用程序日志：

```
heroku logs --tail -a [app-name]
```

现在确保在你的插件清单文件 [这里](/.well-known/ai-plugin.json) 和你的 OpenAPI 模式 [这里](/.well-known/openapi.yaml) 中更改插件的 URL，并使用 `make heroku-push` 重新部署。该 URL 将为 `https://your-app-name.herokuapp.com`。

### Other Deployment Options

一些可能的其他部署选项包括：

- Azure 容器应用：这是一种云平台，允许你使用 Docker 容器部署和管理 Web 应用程序。你可以使用 Azure CLI 或 Azure Portal 来创建和配置你的应用服务，然后将 Docker 镜像推送到容器注册表并部署到你的应用服务中。你还可以使用 Azure Portal 设置环境变量并扩展你的应用程序。了解更多信息，请单击 [此处](https://learn.microsoft.com/en-us/azure/container-apps/get-started-existing-container-image-portal?pivots=container-apps-private-registry)。
- Google Cloud Run：这是一种无服务器平台，允许你使用 Docker 容器运行无状态的 Web 应用程序。你可以使用 Google Cloud Console 或 gcloud 命令行工具来创建和部署 Cloud Run 服务，然后将 Docker 镜像推送到 Google Container Registry 并部署到你的服务中。你还可以使用 Google Cloud Console 设置环境变量并扩展你的应用程序。了解更多信息，请单击 [此处](https://cloud.google.com/run/docs/quickstarts/build-and-deploy)。
- AWS 弹性容器服务：这是一种云平台，允许你使用 Docker 容器运行和管理 Web 应用程序。你可以使用 AWS CLI 或 AWS Management Console 来创建和配置你的 ECS 集群，然后将 Docker 镜像推送到 Amazon Elastic Container Registry 并部署到你的集群中。你还可以使用 AWS Management Console 设置环境变量并扩展你的应用程序。了解更多信息，请单击 [此处](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/docker-basics.html)。

创建应用程序后，请确保在你的插件清单文件 [这里](/.well-known/ai-plugin.json) 和你的 OpenAPI 模式 [这里](/.well-known/openapi.yaml) 中更改插件的 URL，并重新部署。

## Installing a Developer Plugin

要安装开发人员插件，请按照以下步骤操作：

- 首先，通过将其部署到你喜欢的托管平台（例如 Fly.io、Heroku 等）来创建你的开发人员插件，并更新清单文件和 OpenAPI 模式中的插件 URL。

- 转到 [ChatGPT](https://chat.openai.com/)，从模型选择器中选择 "Plugins"。

- 从插件选择器中，滚动到底部，然后点击 "Plugin store"。

- 转到 "Develop your own plugin" 并按照提供的说明操作。你需要输入插件部署的域。

- 根据你为插件选择的认证类型（例如，如果你的插件使用 Service Level HTTP，则必须粘贴你的访问令牌，然后将插件流中收到的新访问令牌粘贴到你的 [ai-plugin.json](/.well-known/ai-plugin.json) 文件中，并重新部署你的应用程序），执行相应的说明。

- 接下来，你必须添加你的插件。再次转到 "Plugin store"，然后点击 "Install an unverified plugin"。

- 按照提供的说明操作，这将要求你输入插件部署的域。

- 根据你为插件选择的认证类型（例如，如果你的插件使用 User Level HTTP，则必须粘贴你的 Bearer 令牌），执行相应的说明。

完成这些步骤后，你的开发人员插件应该已经安装并准备好在 ChatGPT 中使用了。

## Webhooks

为了保持存储在向量数据库中的文档的最新状态，考虑使用工具，如 [Zapier](https://zapier.com) 或 [Make](https://www.make.com)，根据事件或时间表配置传入的 Webhooks 到你的插件 API。例如，这可以让你在更新笔记或接收电子邮件时同步新信息。你还可以使用 [Zapier Transfer](https://zapier.com/blog/zapier-transfer-guide/) 批量处理一组现有文档并将它们上传到向量数据库。

如果你需要将自定义字段从这些工具传递给你的插件，你可能需要创建一个额外的检索插件 API 端点，调用数据存储的 upsert 函数，例如 `upsert-email`。这个自定义端点可以被设计为接受来自 Webhook 的特定字段并相应地处理它们。

要设置传入的 Webhook，请按照以下一般步骤操作：

- 选择一个 Webhook 工具，如 Zapier 或 Make，并创建一个帐户。
- 在工具中设置一个新的 Webhook 或转移，并根据事件或时间表配置它。
- 指定 Webhook 的目标 URL，应该是你的检索插件的 API 端点（例如，`https://your-plugin-url.com/upsert`）。
- 配置 Webhook 负载以包括必要的数据字段，并根据你的检索插件的 API 要求格式化它们。
- 测试 Webhook 以确保它正常工作，并按预期将数据发送到你的检索插件。

设置 Webhook 后，你可能需要运行一个回填来确保向量数据库中包含任何之前遗漏的数据。

请记住，如果你想使用传入的 Webhook 连续同步数据，你应该考虑在设置这些后运行一个回填，以避免遗漏任何数据。

除了使用 Zapier 和 Make 等工具外，你还可以构建自己的自定义集成来与你的检索插件同步数据。这允许你更好地控制数据流，并根据你的特定需求和要求定制集成。

## Scripts

`scripts` 文件夹包含批量插入或处理来自不同数据源的文本文档的脚本，例如 zip 文件、JSON 文件或 JSONL 文件。这些脚本使用插件的 upsert 工具函数将文档及其元数据上传到向量数据库，将它们转换为纯文本并将它们分成块之后。每个脚本文件夹都有一个 README 文件，说明如何使用它以及它需要哪些参数。你还可以使用 [`services.pii_detection`](/services/pii_detection.py) 模块使用语言模型筛选个人身份信息（PII）并跳过它们，这可以在你不希望意外上传敏感或私人文档到向量数据库时有所帮助。此外，你还可以使用 [`services.extract_metadata`](/services/extract_metadata.py) 模块使用语言模型从文档文本中提取元数据，这可以在你希望丰富文档元数据时有所帮助。**注意:** 如果使用传入的 Webhook 连续同步数据，请考虑在设置这些后运行回填，以避免遗漏任何数据。

这些脚本包括：

- [`process_json`](scripts/process_json/)：该脚本处理 JSON 格式的文档文件，并存储它们及其元数据到向量数据库中。JSON 文件的格式应该是一个 JSON 对象的列表，其中每个对象代表一个文档。JSON 对象应该有一个 `text` 字段和其他可选字段以填充元数据。你可以提供自定义元数据作为 JSON 字符串，并提供标志筛选 PII 和提取元数据。
- [`process_jsonl`](scripts/process_jsonl/)：该脚本处理 JSONL 格式的文档文件，并存储它们及其元数据到向量数据库中。JSONL 文件的格式应该是一个由换行符分隔的 JSON 文件，其中每行是一个有效的 JSON 对象，代表一个文档。JSON 对象应该有一个 `text` 字段和其他可选字段以填充元数据。你可以提供自定义元数据作为 JSON 字符串，并提供标志筛选 PII 和提取元数据。
- [`process_zip`](scripts/process_zip/)：该脚本处理 zip 格式的文档文件，并存储它们及其元数据到向量数据库中。zip 文件的格式应该是一个包含 docx、pdf、txt、md、pptx 或 csv 文件的扁平化 zip 文件夹。你可以提供自定义元数据作为 JSON 字符串，并提供标志筛选 PII 和提取元数据。

## Limitations

虽然 ChatGPT 检索插件旨在提供灵活的语义搜索和检索解决方案，但它确实有一些限制：

- **关键词搜索限制**：`text-embedding-ada-002` 模型生成的嵌入可能并不总是有效地捕捉到关键词的精确匹配。因此，对于严重依赖于特定关键词的查询，插件可能无法返回最相关的结果。一些向量数据库，如 Weaviate，使用混合搜索，可能在关键词搜索方面表现更好。
- **敏感数据处理**：插件不会自动检测或过滤敏感数据。开发人员有责任确保他们有必要的授权将内容包含在检索插件中，并且内容符合数据隐私要求。
- **可扩展性**：插件的性能可能会因所选择的向量数据库提供商和数据集的大小而异。一些提供商可能提供更好的可扩展性和性能。
- **语言支持**：插件目前使用的是 OpenAI 的 `text-embedding-ada-002` 模型，该模型针对英语进行了优化。但是，它仍然足够强大，可以为各种语言生成良好的结果。
- **元数据提取**：可选的元数据提取功能依赖于语言模型从文档文本中提取信息。该过程可能不总是准确的，并且提取的元数据的质量可能取决于文档内容和结构。
- **PII 检测**：可选的 PII 检测功能并不是百分百可靠，可能无法捕捉到所有个人身份信息的实例。请谨慎使用此功能，并验证它在您特定的用例中的有效性。

## Future Directions

ChatGPT 检索插件提供了一个灵活的语义搜索和检索解决方案，但始终存在进一步发展的潜力。我们鼓励用户通过提交新功能或增强性的拉取请求来为该项目做出贡献。显著的贡献可能会获得 OpenAI 学分的认可。

一些未来方向的想法包括：

- **更多的向量数据库提供商**：如果您有兴趣将另一个向量数据库提供商与 ChatGPT 检索插件集成，可以提交实现。
- **附加脚本**：扩展可用于从各种数据源处理和上传文档的脚本范围，将使插件更加通用。
- **用户界面**：为管理文档和与插件交互开发用户界面可以改善用户体验。
- **混合搜索 / TF-IDF 选项**：增强 [datastore 的 upsert 函数](/datastore/datastore.py#L18)，提供使用混合搜索或 TF-IDF 索引的选项，可以提高基于关键字的查询的插件性能。
- **高级分块策略和嵌入计算**：实现更复杂的分块策略和嵌入计算，如嵌入文档标题和摘要，对文档块和摘要进行加权平均，或计算文档的平均嵌入，可以获得更好的搜索结果。
- **自定义元数据**：允许用户向文档块添加自定义元数据，如标题或其他相关信息，可能会在某些用例中改善检索结果。
- **附加的可选服务**：集成更多的可选服务，如文档摘要或在嵌入文档之前进行预处理，可以增强插件的功能和检索结果的质量。这些服务可以使用语言模型实现，并直接集成到插件中，而不仅仅在脚本中可用。

我们欢迎社区贡献，以帮助改进 ChatGPT 检索插件并扩展其功能。如果您有想法或功能要贡献，请提交拉取请求到该存储库。

## Contributors

我们要感谢以下贡献者对 ChatGPT 检索插件进行代码/文档贡献和支持，以将各种向量数据库提供商集成到该插件中：

- [Pinecone](https://www.pinecone.io/)
    - [acatav](https://github.com/acatav)
    - [gkogan](https://github.com/gkogan)
    - [jamescalam](https://github.com/jamescalam)
- [Weaviate](https://www.semi.technology/)
    - [hsm207](https://github.com/hsm207)
    - [sebawita](https://github.com/sebawita)
    - [byronvoorbach](https://github.com/byronvoorbach)
- [Zilliz](https://zilliz.com/)
    - [filip-halt](https://github.com/filip-halt)
- [Milvus](https://milvus.io/)
    - [filip-halt](https://github.com/filip-halt)
- [Qdrant](https://qdrant.tech/)
    - [kacperlukawski](https://github.com/kacperlukawski)
- [Redis](https://redis.io/)
    - [tylerhutcherson](https://github.com/tylerhutcherson)
