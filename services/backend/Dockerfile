# services/backend/Dockerfile

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN pip install uv

COPY pyproject.toml ./
COPY uv.lock ./
COPY .env ./
COPY ./assets ./assets

RUN uv sync  

COPY ./services/backend/app ./app

EXPOSE 8000
