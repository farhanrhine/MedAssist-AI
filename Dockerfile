## Parent image — Python 3.12 slim (matches pyproject.toml requires-python)
FROM python:3.12-slim

## Essential environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

## Work directory inside the docker container
WORKDIR /app

## Installing system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

## Install uv — fast Python package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

## Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock .python-version ./

## Install dependencies using uv (without dev deps, frozen lockfile)
RUN uv sync --frozen --no-dev --no-install-project

## Copy the rest of the project
COPY app/ app/
COPY data/ data/
COPY vectorstore/ vectorstore/
COPY main.py .

## Expose Flask port
EXPOSE 5000

## Run the Flask app using uv
CMD ["uv", "run", "python", "-m", "app.application"]
