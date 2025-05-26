# tasks/model_loading.py (oder ähnlich)
import os
import joblib
from prefect import task
from typing import Dict, Any 
import lightgbm as lgb 

FORECAST_TIME_WINDOW = 48
MODEL_PATH = "./models"

@task(name="Load All Trained Models")
def load_all_trained_models_task(model_base_path: str, forecast_window: int) -> Dict[int, Any]:
    """Lädt alle trainierten Modelle für die Vorhersagehorizonte."""
    trained_models = {}
    print(f"Lade Modelle aus: {model_base_path}")
    for h in range(1, forecast_window + 1):
        model_filename = f"temp_forecast_lgbm_model_h{h}.joblib" 
        model_full_path = os.path.join(model_base_path, model_filename)
        try:
            if os.path.exists(model_full_path):
                model = joblib.load(model_full_path)
                trained_models[h] = model
                print(f"Modell für Horizont {h}h geladen von: {model_full_path}")
            else:
                print(f"WARNUNG: Modelldatei nicht gefunden für Horizont {h}h unter {model_full_path}")
                trained_models[h] = None 
        except Exception as e:
            print(f"FEHLER beim Laden des Modells für Horizont {h}h von {model_full_path}: {e}")
            trained_models[h] = None 
            
    if not any(trained_models.values()): 
        raise FileNotFoundError("Keine Modelle konnten geladen werden. Überprüfe MODEL_PATH und Dateinamen.")
        
    return trained_models