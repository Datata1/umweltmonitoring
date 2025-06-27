# services/backend/Dockerfile

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y libgomp1 curl --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml ./
# COPY uv.lock ./
COPY .env ./
COPY ./assets ./assets

RUN uv sync 

EXPOSE 8000
