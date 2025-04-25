# services/ml_service/Dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN pip install uv
COPY pyproject.toml ./ 
COPY uv.lock ./ 
RUN uv  sync 

COPY ./services/ml_service/flows /app/flows
COPY ./services/ml_service/tasks /app/tasks
COPY ./services/ml_service/utils /app/utils

COPY ./services/ml_service/utils/prefect_worker.sh /app/utils/prefect_worker.sh
RUN chmod +x /app/utils/prefect_worker.sh


