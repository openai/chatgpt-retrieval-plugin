# Deploying to Gold Retriever

[goldretriever](https://github.com/jina-ai/GoldRetriever) is an open-source CLI tool, powered by [jina](https://github.com/jina-ai/jina) and [docarray](https://github.com/docarray/docarray), that enables you to create and host ChatGPT retrieval plugins in a few simple steps.

### Installation
Ensure you have Python 3.8 or later:
```shell
pip install goldretriever 
```

### Deployment
Deploy a plugin providing your OpenAI key:
```shell
goldretriever deploy --key <your openai key>
```

Store the "Gateway (Http)" URL and the Bearer token provided in the output.
```shell
╭──────────────────────── 🎉 Flow is available! ────────────────────────╮
│                                                                       │
│   ID               retrieval-plugin-<plugin id>                       │
│   Gateway (Http)   https://retrieval-plugin-<plugin id>.wolf.jina.ai  │
│   Dashboard        https://dashboard.wolf.jina.ai/flow/<plugin id>    │
│                                                                       │
╰───────────────────────────────────────────────────────────────────────╯
Bearer token: <your bearer token>
```

### Data Indexing
Gather relevant text data files (PDF, TXT, DOCX, PPTX, or MD) in a directory and index the data:
```shell
goldretriever index --data my_files
```

### Integration
1. Go to OpenAI Plugins.
2. Select "Develop your own plugin".
3. Enter the "Gateway (Http)" URL and Bearer token from the deployment step.

To learn more, feel free to visit [goldretriever](https://github.com/jina-ai/GoldRetriever) and take a look at this [blogpost](https://jina.ai/news/gold-retriever-let-chatgpt-talk-to-your-data/) that highlights one of the many ways you can use goldretriever.
