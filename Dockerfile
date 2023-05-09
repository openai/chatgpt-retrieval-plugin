
FROM python:3.10.10-slim-buster as base-image

ARG DEPENDENCY_GROUPS="default"

    # python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    \
    # pip
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PRE=1 \
    \
    # poetry
    POETRY_VERSION=1.3.2 \
    POETRY_NO_INTERACTION=1 \
    \
    # paths
    WORKDIR_PATH=/code \
    VENV_PATH=/venv

WORKDIR $WORKDIR_PATH

FROM base-image as build-image

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install "poetry==$POETRY_VERSION" \
    && python3 -m venv $VENV_PATH

COPY poetry.lock pyproject.toml ./
RUN --mount=type=cache,target=/home/.cache/pypoetry/cache \
    --mount=type=cache,target=/home/.cache/pypoetry/artifacts \
    . $VENV_PATH/bin/activate && poetry install --no-root --with $DEPENDENCY_GROUPS

FROM base-image as runtime-image

ENV PATH="$VENV_PATH/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build-image $WORKDIR_PATH/poetry.lock poetry.lock
COPY --from=build-image $WORKDIR_PATH/pyproject.toml pyproject.toml
COPY --from=build-image $VENV_PATH $VENV_PATH

RUN groupadd -r chatgpt && useradd -r -s /bin/false -g chatgpt chatgpt \
    && chown -R chatgpt:chatgpt $WORKDIR_PATH
USER chatgpt

COPY . .

# Heroku uses PORT, Azure App Services uses WEBSITES_PORT, Fly.io uses 8080 by default
CMD ["sh", "-c", "uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-${WEBSITES_PORT:-8080}}"]
