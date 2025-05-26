import os
import sys
import pandas as pd
import numpy as np
from prefect import flow, task
from prefect_dask.task_runners import DaskTaskRunner
from prefect.futures import PrefectFuture
from typing import Dict, List, Any
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tasks.fetch_data import fetch_sensor_data_for_ml
from tasks.data_transformations import transform_data, create_ml_features
from tasks.ml_training import train_single_model
from utils.config import settings

# TODO: flow scheduled each hour should generate prdictions so that we can plot the results. Furthermore we could analyse the prediction error
# in the future if time allows we could implement some sort of context/data drift detection 

@flow(
        task_runner=DaskTaskRunner(
            num_workers=3
        )
)
async def create_predictions_flow():
    """
    Main flow to create predictions for all sensors.
    """
    pass