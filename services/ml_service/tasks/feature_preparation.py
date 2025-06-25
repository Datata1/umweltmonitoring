# tasks/feature_preparation.py (oder ähnlich)
import pandas as pd
from prefect import task
from typing import Dict, Tuple

from .fetch_data import fetch_sensor_data_for_ml 
from .data_transformations import create_ml_features

@task(name="Get Latest Features for Prediction")
async def get_latest_features_for_prediction_task(
    fetch_data_task_fn, 
    create_features_task_fn, 
    lookback_days_for_plot: int = 7
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    """
    Holt die neuesten Daten, erstellt Features für die aktuelle Vorhersage
    und gibt die Features sowie historische Daten für den Plot zurück.
    """
    print("Hole neueste Daten und erstelle aktuelle Features...")
    
    recent_hourly_data = fetch_data_task_fn() 
    
    if recent_hourly_data.empty:
        raise ValueError("Keine aktuellen Daten zum Erstellen von Features erhalten.")

    current_time_for_features = recent_hourly_data.index.max()
    print(f"Aktueller Zeitstempel für Feature-Generierung: {current_time_for_features}")

    features_dict = create_features_task_fn(recent_hourly_data.copy()) 
    X_all_recent = features_dict["X"] 
    
    if X_all_recent.empty:
        raise ValueError("Feature-Matrix X ist leer nach der Verarbeitung der aktuellen Daten.")

    if current_time_for_features in X_all_recent.index:
        latest_feature_row_X = X_all_recent.loc[[current_time_for_features]]
    else:
        print(f"WARNUNG: Genaue Zeit {current_time_for_features} nicht im Index von X_all_recent gefunden. Nehme letzte verfügbare Zeile.")
        latest_feature_row_X = X_all_recent.iloc[[-1]]
        current_time_for_features = latest_feature_row_X.index[0] 
        print(f"Angepasster Zeitstempel für Feature-Generierung (basierend auf X): {current_time_for_features}")

    plot_start_time = current_time_for_features - pd.Timedelta(days=lookback_days_for_plot)
    historical_data_for_plot = recent_hourly_data[
        (recent_hourly_data.index <= current_time_for_features) &
        (recent_hourly_data.index >= plot_start_time)
    ][['temperatur']]

    print(f"Neueste Feature-Zeile (X) für Vorhersage erstellt (Shape: {latest_feature_row_X.shape}).")
    print(f"Historische Daten für Plot vorbereitet (Shape: {historical_data_for_plot.shape}).")
    
    return latest_feature_row_X, historical_data_for_plot, current_time_for_features