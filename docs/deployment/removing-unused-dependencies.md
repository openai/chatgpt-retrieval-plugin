# Removing Unused Dependencies

You can specify the packages to install based on each vector database provider:

- **Pinecone:** `docker build . -t [image_name] --build-arg DEPENDENCY_GROUPS=pinecone`
- **Weaviate:** `docker build . -t [image_name] --build-arg DEPENDENCY_GROUPS=weaviate`
- **Zilliz:** `docker build . -t [image_name] --build-arg DEPENDENCY_GROUPS=zilliz`
- **Milvus:** `docker build . -t [image_name] --build-arg DEPENDENCY_GROUPS=milvus`
- **Qdrant:** `docker build . -t [image_name] --build-arg DEPENDENCY_GROUPS=qdrant`
- **Redis:** `docker build . -t [image_name] --build-arg DEPENDENCY_GROUPS=redis`
- **LLamaIndex:** `docker build . -t [image_name] --build-arg DEPENDENCY_GROUPS=llama`
