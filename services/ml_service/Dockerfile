# services/ml_service/Dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && \
    apt-get install -y libgomp1 --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

    
WORKDIR /app
RUN pip install uv
COPY pyproject.toml ./ 
# COPY uv.lock ./ 
RUN uv  sync 


COPY ./services/ml_service ./app/
COPY .env ./services/ml_service/utils/.env



