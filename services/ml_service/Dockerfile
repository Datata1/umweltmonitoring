# services/ml_service/Dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN pip install uv
COPY pyproject.toml ./ 
# COPY uv.lock ./ 
RUN uv  sync 


COPY ./services/ml_service ./app/
COPY .env ./



