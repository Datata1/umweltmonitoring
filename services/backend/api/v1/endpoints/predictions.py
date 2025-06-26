# services/backend/app/api/v1/endpoints/sensors.py
import logging
import os
import joblib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from fastapi import Depends, HTTPException, APIRouter
from pydantic import BaseModel

from sqlalchemy.orm import Session
import pandas as pd
import numpy as np


from custom_types.prediction import TrainedModel 
from utils.db_session import get_db
from utils.feature_enhancer import get_solar_features, get_weather_features 
from utils.data_transformations import create_features_for_prediction 
from shared.crud import crud_sensor

# --- Konfiguration ---
MODEL_PATH = "/app/backend/models"
FORECAST_HORIZON = 48
TEMPERATURE_SENSOR_ID = "5faeb5589b2df8001b980307"
TIMEZONE = "Europe/London"


router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# === 3. Pydantic-Modelle (für die API-Antworten) ===
class ModelResponse(BaseModel):
    id: int
    model_name: str
    forecast_horizon_hours: int
    model_path: str
    last_trained_at: datetime
    val_rmse: Optional[float] = None
    val_mae: Optional[float] = None

    class Config:
        orm_mode = True 

class PredictionPoint(BaseModel):
    timestamp: datetime
    value: Optional[float]
    type: str 

class PredictionResponse(BaseModel):
    plot_data: List[PredictionPoint]
    last_updated: datetime
    message: str

loaded_models = {"models": {}, "timestamp": None}

def load_prediction_models(db: Session) -> Dict[int, Any]:
    """
    Lädt alle trainierten Modelle aus der Datenbank und vom Dateisystem.
    Korrigiert den Pfad zur Laufzeit, um zur Umgebung des Backends zu passen.
    """
    cache_age = (datetime.now() - loaded_models["timestamp"]) if loaded_models["timestamp"] else timedelta(minutes=60)
    
    if not loaded_models["models"] or cache_age > timedelta(minutes=15):
        print("Lade Modelle neu oder aktualisiere Cache...")
        db_models = db.query(TrainedModel).all()
        models = {}
        for db_model in db_models:
            try:
                filename = os.path.basename(db_model.model_path)
                
                correct_path_in_backend = os.path.join(MODEL_PATH, filename)
                
                if os.path.exists(correct_path_in_backend):
                    model_object = joblib.load(correct_path_in_backend)
                    models[db_model.forecast_horizon_hours] = model_object
                else:
                    print(f"WARNUNG: Modelldatei nicht gefunden unter: {correct_path_in_backend}")
            except Exception as e:
                print(f"FEHLER beim Laden des Modells {correct_path_in_backend}: {e}")
        
        loaded_models["models"] = models
        loaded_models["timestamp"] = datetime.now()
        return models
    else:
        print("Verwende Modelle aus dem Cache.")
        return loaded_models["models"]


# === 6. API-Endpunkte ===

@router.get("/models", response_model=List[ModelResponse], tags=["Models"])
def get_models(db: Session = Depends(get_db)):
    """
    Gibt eine Liste aller trainierten Modelle und ihrer Metriken aus der Datenbank zurück.
    """
    models = db.query(TrainedModel).order_by(TrainedModel.forecast_horizon_hours).all()
    return models


@router.get("/predictions", tags=["Predictions"]) # response_model entfernt für Flexibilität mit isoformat
def get_predictions(db: Session = Depends(get_db)):
    """
    Erstellt eine neue Temperaturvorhersage.
    
    Dieser Endpunkt kombiniert historische Daten mit den neuen Vorhersagen,
    um einen vollständigen Datensatz für einen Plot zu erstellen. Alle Zeitstempel
    werden konsistent in UTC im ISO 8601 Format zurückgegeben.
    """
    try:
        models = load_prediction_models(db)
        if not models:
            raise HTTPException(status_code=404, detail="Keine trainierten Modelle gefunden.")

        # --- KORRIGIERTER TEIL: Hole Daten direkt aus der DB via CRUD ---
        # 1. Hole die neuesten historischen Rohdaten. Verwende timezone.utc.
        # KORREKTUR: Verwende timezone.utc für konsistente, zeitzonenbewusste Abfragen
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(days=31)
        
        aggregated_data = crud_sensor.sensor_data.get_aggregated_data_by_sensor_id(
            db,
            sensor_id=TEMPERATURE_SENSOR_ID,
            from_date=from_date,
            to_date=to_date,
            interval='1h',
            aggregation_type='avg'
        )

        if not aggregated_data:
            raise HTTPException(status_code=404, detail="Keine historischen Daten zum Erstellen von Features gefunden.")

        # 2. Konvertiere die DB-Objekte in ein sauberes Pandas DataFrame
        historical_records = [
            {"timestamp": item['time_bucket'], "temperatur": item['aggregated_value']} 
            for item in aggregated_data
        ]        
        # pd.to_datetime wandelt die Zeitstempel aus der DB (vermutlich UTC) korrekt um
        historical_df = pd.DataFrame(historical_records)
        historical_df['timestamp'] = pd.to_datetime(historical_df['timestamp'])
        historical_df = historical_df.set_index('timestamp').sort_index().interpolate(method='linear')
        

        # 4. Erstelle Features für den letzten verfügbaren Zeitpunkt
        latest_features = create_features_for_prediction(historical_df)
        
        # 5. Generiere die Vorhersagen
        predictions = []
        last_known_timestamp = latest_features.index[0]

        if last_known_timestamp.tzinfo is None:
            # Wenn der Zeitstempel "naiv" ist, lokalisiere ihn als UTC.
            last_known_timestamp = last_known_timestamp.tz_localize('UTC')
        else:
            # Wenn er eine andere Zeitzone hat, konvertiere ihn zu UTC.
            last_known_timestamp = last_known_timestamp.tz_convert('UTC')

        for h in range(1, FORECAST_HORIZON + 1):
            model = models.get(h)
            # KORREKTUR: Konvertiere den Zeitstempel direkt in einen ISO-String
            pred_timestamp = (last_known_timestamp + timedelta(hours=h)).isoformat()
            pred_point = {"timestamp": pred_timestamp, "value": None, "type": "predicted"}
            
            if model:
                try:
                    pred_value = model.predict(latest_features)[0]
                    pred_point["value"] = float(pred_value)
                except Exception as e:
                    logger.error(f"Vorhersagefehler bei Horizont {h}: {e}")
            predictions.append(pred_point)
        
        # 6. Kombiniere historische und vorhergesagte Daten
        historical_data = [
            # KORREKTUR: Konvertiere auch hier den Zeitstempel in einen ISO-String
            {"timestamp": ts.isoformat(), "value": val, "type": "historical"}
            for ts, val in historical_df['temperatur'].items()
        ]

        full_plot_data = historical_data + predictions

        return {
            "plot_data": full_plot_data,
            # KORREKTUR: Verwende datetime.now(timezone.utc) und isoformat
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "message": f"{FORECAST_HORIZON}-Stunden-Vorhersage erfolgreich erstellt."
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unerwarteter Fehler im /predictions Endpunkt: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Ein interner Fehler ist aufgetreten.")

