import os
import sys

from prefect import flow, task
from prefect_dask.task_runners import DaskTaskRunner
from prefect.futures import PrefectFuture
from prefect.artifacts import create_markdown_artifact 


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tasks.fetch_data import fetch_sensor_data_for_ml
from tasks.data_transformations import transform_data, create_ml_features
from tasks.ml_training import train_single_model
from utils.config import settings

FORECAST_TIME_WINDOW = 48  # Stunden in die Zukunft
MODEL_PATH = "./models"

@flow(
        task_runner=DaskTaskRunner(
            cluster_kwargs={
                "n_workers": 3
            }
        )
)
async def train_all_models():

    # 1. get data from sensors
    sensor_data= fetch_sensor_data_for_ml()

    # == debug == 
    markdown_output = sensor_data.head(10).to_markdown(index=True)

    await create_markdown_artifact(
        key="sensor-data-sample",
        markdown=f"## Vorschau der Sensordaten (erste 10 Zeilen)\n\n{markdown_output}",
        description="debug"
    )


    # 3. create features for ML (lag features, rolling means, sin/cos transformations, etc.)
    # features_data = create_ml_features(transformed_data)

    # 4. train models for temperature sensor
    # for h in range(FORECAST_TIME_WINDOW):
    #     train model for h
    # train_single_model(features_data)

    # 5. create artefact of training metrics


    pass