# tasks/data_transformations.py

import requests
from typing import Dict, Any, List 
from prefect import task, get_run_logger
from datetime import datetime, timezone, timedelta 
from sqlalchemy.exc import SQLAlchemyError 
import pandas as pd

from utils.db_utils import get_db_session

from shared.crud import crud_sensor
from shared.schemas import sensor as sensor_schema
from utils.parse_datetime import parse_api_datetime


@task(
    name="Create ML Features"
)
def create_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Erstellt Features für das ML-Modell aus den transformierten Daten.
    """
    pass