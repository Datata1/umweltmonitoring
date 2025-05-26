# Haupt-Flow-Datei (z.B. flows/forecasting.py)
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd # Sicherstellen, dass pandas importiert ist
from prefect import flow
from prefect.artifacts import create_markdown_artifact
import base64 # Für die Konvertierung des Bildes

from utils.config import settings 
from tasks.fetch_data import fetch_sensor_data_for_ml
from tasks.data_transformations import create_ml_features 
from tasks.load_models import load_all_trained_models_task
from tasks.feature_preparation import get_latest_features_for_prediction_task
from tasks.predictions import generate_all_predictions_task
from tasks.plotting import create_forecast_plot_task

FORECAST_TIME_WINDOW = 48 
MODEL_PATH = "./models"   


@flow(name="Generate Forecast and Plot", log_prints=True)
async def generate_forecast_flow():
    print("Starte Vorhersage-Flow...")

    # 1. Trainierte Modelle laden
    trained_models = load_all_trained_models_task(
        model_base_path=MODEL_PATH,
        forecast_window=FORECAST_TIME_WINDOW
    )
    if not any(trained_models.values()): 
        print("FEHLER: Keine Modelle geladen, Vorhersage nicht möglich.")
        await create_markdown_artifact(key="forecast_status", markdown="## Vorhersage Fehlgeschlagen\n\nKeine trainierten Modelle gefunden.", description="Vorhersagestatus")
        return

    # 2. Aktuellste Features für die Vorhersage holen + historische Daten für Plot
    latest_X_features, historical_data_for_plot, prediction_start_base_time = await get_latest_features_for_prediction_task(
        fetch_data_task_fn=fetch_sensor_data_for_ml,
        create_features_task_fn=create_ml_features, 
        lookback_days_for_plot=21 
    )

    # 3. Vorhersagen generieren
    forecast_start_timestamp = prediction_start_base_time + pd.Timedelta(hours=1)
    
    forecast_df = await generate_all_predictions_task(
        current_features_df=latest_X_features,
        trained_models=trained_models,
        forecast_window=FORECAST_TIME_WINDOW,
        prediction_start_time=forecast_start_timestamp
    )

    # 4. Plot erstellen
    plot_image_bytes = await create_forecast_plot_task(
        historical_data_df=historical_data_for_plot,
        forecast_df=forecast_df
    )

    # 5. Plot als Markdown-Artefakt mit Base64-kodiertem Bild speichern
    base64_image = base64.b64encode(plot_image_bytes).decode('utf-8')
    markdown_content = (
        f"## Temperaturvorhersage ({pd.Timestamp.now(tz='Europe/Berlin').strftime('%Y-%m-%d %H:%M:%S %Z')})\n\n"
        f"Vorhersage für die nächsten {FORECAST_TIME_WINDOW} Stunden, beginnend ab {forecast_start_timestamp.strftime('%Y-%m-%d %H:%M')}:\n\n"
        f"![Forecast Plot](data:image/png;base64,{base64_image})"
    )
    
    await create_markdown_artifact(
        key="forecast-plot-with-history",
        markdown=markdown_content,
        description="Visualisierung der historischen Temperatur und der aktuellen 48h-Vorhersage."
    )

    print("Vorhersage-Flow erfolgreich abgeschlossen. Plot-Artefakt erstellt.")
