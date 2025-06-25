# tasks/prediction.py (oder ähnlich)
import pandas as pd
from prefect import task
from typing import Dict, Any

@task(name="Generate All Predictions")
async def generate_all_predictions_task(
    current_features_df: pd.DataFrame,
    trained_models: Dict[int, Any],   
    forecast_window: int,
    prediction_start_time: pd.Timestamp 
) -> pd.DataFrame:
    """Erstellt Vorhersagen für alle Horizonte."""
    predictions = []
    prediction_timestamps = []

    if current_features_df.empty:
        raise ValueError("Feature DataFrame für die Vorhersage ist leer.")
    if not trained_models:
        raise ValueError("Keine trainierten Modelle für die Vorhersage übergeben.")
    

    print(f"Generiere Vorhersagen für {forecast_window} Stunden ab {prediction_start_time}...")
    for h in range(1, forecast_window + 1):
        model = trained_models.get(h)

        if model:
            try:
                pred_value = model.predict(current_features_df)[0]
                predictions.append(pred_value)
                prediction_timestamps.append(prediction_start_time + pd.Timedelta(hours=h-1)) 
            except Exception as e:
                print(f"FEHLER bei Vorhersage für Horizont {h}h: {e}. Setze Vorhersage auf NaN.")
                predictions.append(pd.NA) # Oder np.nan
                prediction_timestamps.append(prediction_start_time + pd.Timedelta(hours=h-1))
        else:
            print(f"WARNUNG: Kein Modell für Horizont {h}h geladen. Setze Vorhersage auf NaN.")
            predictions.append(pd.NA)
            prediction_timestamps.append(prediction_start_time + pd.Timedelta(hours=h-1))
            
    forecast_df = pd.DataFrame({'forecast_timestamp': prediction_timestamps, 'predicted_temp': predictions})
    forecast_df.set_index('forecast_timestamp', inplace=True)
    
    print(f"Vorhersagen generiert (Shape: {forecast_df.shape}).")
    return forecast_df