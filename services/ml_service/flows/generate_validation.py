# Haupt-Flow-Datei (z.B. flows/forecasting.py)
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact
from typing import Dict, Any, Union
import numpy as np

from tasks.predictions import generate_all_predictions_task
from sklearn.metrics import mean_absolute_error, r2_score

MODEL_PATH = "./models"
FORECAST_TIME_WINDOW = 24

def calculate_robust_maep(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    valid_mask = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true_valid = y_true[valid_mask]
    y_pred_valid = y_pred[valid_mask]

    if len(y_true_valid) == 0:
        return np.nan

    absolute_percentage_errors = np.abs((y_true_valid - y_pred_valid) / (y_true_valid + 1e-8))

    return np.mean(absolute_percentage_errors) * 100


@flow(name="Generate Validation, Plot", log_prints=True)
async def generate_validation_flow(
    X_val: Union[np.ndarray, pd.DataFrame, pd.Series],
    y_val: Union[np.ndarray, pd.DataFrame, pd.Series],
    trained_models: Dict[int, Any]
) -> pd.DataFrame:
    if X_val.empty or y_val.empty:
        print("X_val oder y_val DataFrame/Series ist leer. Keine Validierung möglich.")
        return pd.DataFrame()
    if not trained_models:
        print("Keine trainierten Modelle für die Validierung übergeben.")
        return pd.DataFrame()

    all_horizon_predictions = {h: [] for h in range(1, FORECAST_TIME_WINDOW + 1)}
    all_horizon_actuals = {h: [] for h in range(1, FORECAST_TIME_WINDOW + 1)}

    if not isinstance(y_val, pd.Series):
        if isinstance(y_val, pd.DataFrame) and y_val.shape[1] == 1:
            y_val = y_val.iloc[:, 0]
        else:
            raise TypeError("y_val muss eine pandas Series oder ein DataFrame mit genau einer Spalte sein.")


    print(f"Starte Validierung über {len(X_val)} potenzielle Startzeitpunkte...")

    for i, current_features_row in X_val.iterrows():
        current_features_df = pd.DataFrame([current_features_row])

        prediction_start_time = i 

        predictions_df = await generate_all_predictions_task(
            current_features_df=current_features_df,
            trained_models=trained_models,
            forecast_window=FORECAST_TIME_WINDOW,
            prediction_start_time=prediction_start_time
        )

        for h in range(1, FORECAST_TIME_WINDOW + 1):
            forecast_timestamp_h = prediction_start_time + pd.Timedelta(hours=h)

            if forecast_timestamp_h in predictions_df.index:
                predicted_value = predictions_df.loc[forecast_timestamp_h, 'predicted_temp']

                if forecast_timestamp_h in y_val.index:
                    actual_value = y_val.loc[forecast_timestamp_h]

                    if pd.notna(predicted_value) and pd.notna(actual_value):
                        all_horizon_predictions[h].append(predicted_value)
                        all_horizon_actuals[h].append(actual_value)

    metrics_by_horizon = {}
    markdown_table_rows = []

    for h in range(1, FORECAST_TIME_WINDOW + 1):
        y_true_h = all_horizon_actuals[h]
        y_pred_h = all_horizon_predictions[h]

        r2, mae, maep = np.nan, np.nan, np.nan

        if len(y_true_h) > 1:
            try:
                mae = mean_absolute_error(y_true_h, y_pred_h)
                maep = calculate_robust_maep(y_true_h, y_pred_h)
                if np.std(y_true_h) != 0:
                    r2 = r2_score(y_true_h, y_pred_h)
                else:
                    r2 = 1.0 if np.allclose(y_true_h, y_pred_h) else np.nan
            except Exception as e:
                print(f"Fehler bei Metrikberechnung für Horizont {h}h: {e}")
        elif len(y_true_h) == 1:
            mae = abs(y_true_h[0] - y_pred_h[0]) if pd.notna(y_true_h[0]) and pd.notna(y_pred_h[0]) else np.nan
            maep = calculate_robust_maep(y_true_h, y_pred_h)
            r2 = np.nan

        metrics_by_horizon[h] = {
            'MAE': mae,
            'MAEP': maep,
            'R2': r2
        }
        markdown_table_rows.append(f"| {h:<12} | {mae:.2f} | {maep:.2f} | {r2:.4f} |")

    markdown_content = (
        "# Validierungsmetriken pro Vorhersagehorizont\n\n"
        "Diese Tabelle zeigt die Performance jedes Vorhersagemodells "
        "für seinen spezifischen Horizont über den gesamten Validierungszeitraum.\n\n"
        "| Horizont (h) | MAE | MAEP (%) | R2 |\n"
        "|--------------|-----|----------|----|\n"
    )
    markdown_content += "\n".join(markdown_table_rows)

    await create_markdown_artifact(
        key="validation-metrics-per-horizon",
        markdown=markdown_content
    )

    print("Validierung erfolgreich abgeschlossen. Metriken pro Horizont als Markdown-Artefakt erstellt.")

    return pd.DataFrame.from_dict(metrics_by_horizon, orient='index')