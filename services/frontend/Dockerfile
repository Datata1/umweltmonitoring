# services/frontend/Dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN pip install uv
COPY pyproject.toml ./
COPY uv.lock ./
RUN uv sync 
COPY ./services/frontend/app /app/app/ 
EXPOSE 8050
