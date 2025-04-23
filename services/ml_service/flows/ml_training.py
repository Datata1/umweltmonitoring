import os
import sys
from datetime import timedelta
from prefect import flow, get_run_logger
from prefect.artifacts import create_markdown_artifact

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.config import settings


@flow(log_prints=True)
async def data_ingestion_flow():
    pass