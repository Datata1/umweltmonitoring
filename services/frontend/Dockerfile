# services/frontend/Dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN pip install uv
COPY pyproject.toml ./
RUN uv sync 
EXPOSE 8050
