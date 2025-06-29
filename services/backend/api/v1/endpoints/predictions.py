# services/backend/app/api/v1/endpoints/sensors.py
import logging
import os
import joblib
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from fastapi import Depends, HTTPException, APIRouter, Response, status
from pydantic import BaseModel, Field
from sklearn.metrics import mean_squared_error, mean_absolute_error


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
    # --- Identifikation & Metadaten ---
    id: int
    model_name: str
    forecast_horizon_hours: int
    model_path: str
    version_id: int
    last_trained_at: datetime
    
    # --- Trainings-Metriken ---
    training_duration_seconds: Optional[float] = None

    # --- Leistungsmetriken (aus der Validierung) ---
    val_mae: Optional[float] = None
    val_rmse: Optional[float] = None
    val_mape: Optional[float] = None # Fehlendes Feld
    val_r2: Optional[float] = None   # Fehlendes Feld

    naive_val_rmse: Optional[float] = None
    naive_val_mae: Optional[float] = None

    class Config:
        from_attributes = True

class PredictionPoint(BaseModel):
    timestamp: datetime
    value: Optional[float]
    type: str 

class PredictionResponse(BaseModel):
    plot_data: List[PredictionPoint]
    last_updated: datetime
    message: str

class HistoricalPredictionPoint(BaseModel):
    timestamp: datetime
    value: Optional[float]

class CalculatedMetrics(BaseModel):
    ml_rmse: Optional[float] = Field(None, alias="val_rmse")
    ml_mae: Optional[float] = Field(None, alias="val_mae")
    naive_rmse: Optional[float] = Field(None, alias="naive_val_rmse")
    naive_mae: Optional[float] = Field(None, alias="naive_val_mae")
    r2_score: Optional[float] = None

class HistoricalPredictionResponse(BaseModel):
    actual_data: List[HistoricalPredictionPoint]
    predicted_data: List[HistoricalPredictionPoint]
    naive_data: List[HistoricalPredictionPoint]
    metrics: CalculatedMetrics


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

def get_validation_data_for_model(model: TrainedModel, db: Session) -> pd.DataFrame:
    """
    Holt die historischen Daten, die als Validierungs-Set für ein gegebenes
    Modell gedient haben könnten.
    
    Diese Funktion holt die Temperaturdaten für einen 30-Tage-Zeitraum,
    der direkt vor dem Trainingszeitpunkt des Modells endet.
    """
    logger.info(f"Lade Validierungsdaten für Modell-ID {model.id}, trainiert am {model.last_trained_at}")
    
    try:
        # End-Datum ist der Zeitpunkt des Trainings
        to_date = model.last_trained_at
        # Start-Datum ist 30 Tage davor
        from_date = to_date - timedelta(days=30)
        
        # Hole die aggregierten stündlichen Daten aus der DB
        aggregated_data = crud_sensor.sensor_data.get_aggregated_data_by_sensor_id(
            db,
            sensor_id=TEMPERATURE_SENSOR_ID,
            from_date=from_date,
            to_date=to_date,
            interval='1h',
            aggregation_type='avg'
        )
        
        if not aggregated_data:
            logger.warning(f"Keine Validierungsdaten für den Zeitraum {from_date} bis {to_date} gefunden.")
            return pd.DataFrame()
            
        # Erstelle einen sauberen DataFrame nur mit den Zielwerten
        records = [{"y_true": item['aggregated_value']} for item in aggregated_data]
        validation_df = pd.DataFrame(records)
        
        logger.info(f"{len(validation_df)} Validierungs-Datenpunkte gefunden.")
        return validation_df

    except Exception as e:
        logger.error(f"Fehler beim Laden der Validierungsdaten für Modell {model.id}: {e}")
        return pd.DataFrame()


# === 6. API-Endpunkte ===

@router.get("/models", response_model=List[ModelResponse], tags=["Models"])
def get_models(limit: int = 24, db: Session = Depends(get_db)):
    """
    Gibt eine limitierte Liste der trainierten Modelle zurück und reichert sie
    mit den Metriken eines naiven Vergleichsmodells an.
    """
    models_from_db = db.query(TrainedModel).order_by(TrainedModel.forecast_horizon_hours).limit(limit).all()
    
    enriched_models = []
    for model in models_from_db:
        # Konvertiere das SQLAlchemy-Objekt in ein Pydantic-Modell
        model_response = ModelResponse.from_orm(model)

        try:
            # 1. Hole die Validierungsdaten für dieses spezifische Modell
            validation_df = get_validation_data_for_model(model, db)
            
            if not validation_df.empty:
                y_true = validation_df['y_true'].values
                
                # 2. Erstelle die Vorhersage des naiven Modells (Wert von 24h vorher)
                y_pred_naive = np.roll(y_true, 24)
                
                # Schneide die ersten 24 Werte ab, da für sie keine Historie existiert
                y_true_valid = y_true[24:]
                y_pred_naive_valid = y_pred_naive[24:]
                
                # 3. Berechne die Fehler für das naive Modell
                if len(y_true_valid) > 0:
                    model_response.naive_val_rmse = np.sqrt(mean_squared_error(y_true_valid, y_pred_naive_valid))
                    model_response.naive_val_mae = mean_absolute_error(y_true_valid, y_pred_naive_valid)
                
        except Exception as e:
            logger.error(f"Fehler bei der Berechnung der naiven Metriken für Modell {model.id}: {e}")
            model_response.naive_val_rmse = None
            model_response.naive_val_mae = None

        enriched_models.append(model_response)
        
    return enriched_models


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

@router.get("/models/{horizon}/historical_predictions", response_model=HistoricalPredictionResponse, tags=["Models"])
def get_historical_predictions_for_model(horizon: int, db: Session = Depends(get_db)):
    """
    Erstellt Vorhersagen für einen historischen Zeitraum und berechnet ON-THE-FLY
    die Performance-Metriken für das ML-Modell und ein naives Modell.
    """
    try:
        logger.info(f"--- Starte Vorhersage & Metrik-Berechnung für Horizont: {horizon}h ---")

        # 1. Modell und historische Daten laden (wie zuvor)
        models = load_prediction_models(db)
        model_object = models.get(horizon)
        if not model_object:
            raise HTTPException(status_code=404, detail=f"Modell für Horizont {horizon}h nicht gefunden.")

        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(days=31)
        
        aggregated_data = crud_sensor.sensor_data.get_aggregated_data_by_sensor_id(
            db, sensor_id=TEMPERATURE_SENSOR_ID, from_date=from_date,
            to_date=to_date, interval='1h', aggregation_type='avg'
        )
        if not aggregated_data:
            raise HTTPException(status_code=404, detail="Keine historischen Daten gefunden.")
        
        historical_records = [{"timestamp": item['time_bucket'], "temperatur": item['aggregated_value']} for item in aggregated_data]
        historical_df = pd.DataFrame(historical_records).set_index('timestamp').sort_index().interpolate(method='linear')
        
        # 2. Vorhersagen für ML- und naives Modell erstellen (wie zuvor)
        features_df = create_features_for_prediction(historical_df, for_all_rows=True)
        predictions_values = model_object.predict(features_df)
        predictions_df = pd.DataFrame(
            data=predictions_values,
            index=features_df.index + pd.to_timedelta(horizon, unit='h'),
            columns=['predicted_value']
        )
        naive_predictions_df = historical_df[['temperatur']].shift(24).rename(columns={'temperatur': 'naive_value'})
        
        # 3. Alle Daten für die Metrik-Berechnung kombinieren
        combined_df = historical_df.join(predictions_df).join(naive_predictions_df)
        # Nur Zeilen behalten, in denen ALLE drei Werte vorhanden sind, um einen fairen Vergleich zu gewährleisten
        metrics_df = combined_df.dropna()
        
        # 4. NEU: Metriken berechnen
        metrics = {}
        if not metrics_df.empty:
            y_true = metrics_df['temperatur']
            y_pred_ml = metrics_df['predicted_value']
            y_pred_naive = metrics_df['naive_value']
            
            metrics['val_rmse'] = np.sqrt(mean_squared_error(y_true, y_pred_ml))
            metrics['val_mae'] = mean_absolute_error(y_true, y_pred_ml)
            metrics['naive_val_rmse'] = np.sqrt(mean_squared_error(y_true, y_pred_naive))
            metrics['naive_val_mae'] = mean_absolute_error(y_true, y_pred_naive)
            # R² Score für das ML-Modell
            metrics['r2_score'] = model_object.score(features_df.loc[y_true.index - pd.to_timedelta(horizon, 'h')], y_true) if hasattr(model_object, 'score') else None
            
            logger.info(f"Metriken für Horizont {horizon}h berechnet: {metrics}")
        else:
            logger.warning(f"Keine überlappenden Daten für Metrik-Berechnung bei Horizont {horizon}h gefunden.")

        # 5. Daten für die API-Antwort formatieren
        actual_data_out = [HistoricalPredictionPoint(timestamp=idx, value=row.temperatur) for idx, row in combined_df.iterrows() if pd.notna(row.temperatur)]
        predicted_data_out = [HistoricalPredictionPoint(timestamp=idx, value=row.predicted_value) for idx, row in combined_df.iterrows() if pd.notna(row.predicted_value)]
        naive_data_out = [HistoricalPredictionPoint(timestamp=idx, value=row.naive_value) for idx, row in combined_df.iterrows() if pd.notna(row.naive_value)]

        return HistoricalPredictionResponse(
            actual_data=actual_data_out,
            predicted_data=predicted_data_out,
            naive_data=naive_data_out,
            metrics=CalculatedMetrics(**metrics)
        )

    except Exception as e:
        logger.error(f"Fehler bei hist. Vorhersage für Horizont {horizon}h: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Interner Fehler bei der Erstellung der historischen Vorhersage.")
    

@router.get("/health/readiness", tags=["Health Check"])
def check_model_readiness(response: Response):
    """
    Überprüft, ob Modelldateien im erwarteten Verzeichnis vorhanden sind.
    
    Gibt 'ready' zurück, wenn mindestens eine Datei gefunden wird, andernfalls 'not ready'.
    Dieser Endpunkt kann für Kubernetes Readiness Probes verwendet werden.
    """
    try:
        # 1. Überprüfen, ob das Verzeichnis überhaupt existiert
        if not os.path.exists(MODEL_PATH) or not os.path.isdir(MODEL_PATH):
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "not ready",
                "detail": f"Model directory not found at: {MODEL_PATH}"
            }
        
        # 2. Überprüfen, ob das Verzeichnis irgendwelche Dateien enthält
        # Wir listen alle Einträge auf und filtern nach Dateien
        model_files = [f for f in os.listdir(MODEL_PATH) if os.path.isfile(os.path.join(MODEL_PATH, f))]
        
        if not model_files:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "not ready",
                "detail": f"No model files found in directory: {MODEL_PATH}"
            }
            
        # 3. Wenn alles in Ordnung ist, 'ready' zurückgeben
        return {"status": "ready"}

    except Exception as e:
        logger.error(f"Fehler bei der Readiness-Prüfung: {e}", exc_info=True)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "error", "detail": "An internal error occurred during readiness check."}



