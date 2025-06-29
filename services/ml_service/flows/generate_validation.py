# Haupt-Flow-Datei (z.B. flows/forecasting.py)
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd # Sicherstellen, dass pandas importiert ist
from prefect import flow
from prefect.artifacts import create_markdown_artifact
from typing import Dict
import base64 # Für die Konvertierung des Bildes
from tasks.predictions import generate_all_predictions_task
from tasks.plotting import create_forecast_plot_task


MODEL_PATH = "./models"
FORECAST_TIME_WINDOW = 24

@flow(name="Generate Validation, Plot", log_prints=True)
async def generate_validation_flow(
    X_val: pd.DataFrame,
    y_val: pd.DataFrame,
    trained_models: Dict
) -> pd.DataFrame:
    validation_start_timestamp = X_val.index.min()

    validation_df = await generate_all_predictions_task(
        current_features_df=X_val,
        trained_models=trained_models,
        forecast_window=FORECAST_TIME_WINDOW,
        prediction_start_time=validation_start_timestamp
    )

    plot_image_bytes = await create_forecast_plot_task(
        historical_data_df=y_val,
        forecast_df=validation_df
    )

    base64_image = base64.b64encode(plot_image_bytes).decode('utf-8')
    markdown_content = (
        f"## Modellvalidierung: Temperaturvorhersage ({pd.Timestamp.now(tz='Europe/Berlin').strftime('%Y-%m-%d %H:%M:%S %Z')})\n\n"
        f"Vorhersage für die nächsten {FORECAST_TIME_WINDOW} Stunden, beginnend ab {validation_start_timestamp.strftime('%Y-%m-%d %H:%M')}:\n\n"
        f"![Validation Plot](data:image/png;base64,{base64_image})"
    )
    
    await create_markdown_artifact(
        key="validation-plot-with-history",
        markdown=markdown_content,
        description="Visualisierung der historischen Temperatur und der Validierungs-Vorhersage."
    )

    print("Validierung erfolgreich abgeschlossen. Plot-Artefakt erstellt.")
