import os
import sys
import datetime
import pandas as pd
from pathlib import Path

from prefect import flow, get_run_logger
from prefect_dask.task_runners import DaskTaskRunner
from prefect.futures import PrefectFuture
from prefect.artifacts import create_markdown_artifact


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tasks.fetch_data import fetch_sensor_data_for_ml
from tasks.data_transformations import create_ml_features
from tasks.ml_training import train_single_model
from utils.db_utils import get_db_session
from utils.db_setup import initialize_database
from utils.training import _update_or_create_model_in_db
from utils.markdown import _create_beautiful_markdown

from generate_validation import generate_validation_flow


FORECAST_TIME_WINDOW = 24

MODEL_PATH = Path("/app/ml_service/models")

@flow(
    name="Train Models",
    description="Trainiert ML-Modelle für die Vorhersage von Sensordaten.",
    log_prints=True,
    task_runner=DaskTaskRunner(
        cluster_kwargs={
            "n_workers": 3
        }
    )
)
async def train_all_models():

    logger = get_run_logger()

    logger.info("Starte ML-Training Flow...")

    # 0. Initialisierung Tabelle models
    initialize_database()

    # 1. get data from sensors
    sensor_data= fetch_sensor_data_for_ml(weeks=16)
    print(len(sensor_data))

    # == debug == 
    markdown_output = sensor_data.head(10).to_markdown(index=True)
    await create_markdown_artifact(
        key="sensor-data-sample",
        markdown=f"## Vorschau der Sensordaten (erste 10 Zeilen)\n\n{markdown_output}",
        description="debug"
    )

    # 2. create features for ML (lag features, rolling means, sin/cos transformations, etc.)
    features_dict = create_ml_features(sensor_data)

    X_train = features_dict["X_train"]
    X_val = features_dict["X_val"]
    X = features_dict["X"]
    Y_targets_train = features_dict["Y_targets_train"]
    Y_targets = features_dict["Y_targets"]
    y_val = sensor_data[sensor_data.index.isin(X_val.index)].copy()  

    processed_data_markdown =   X_train.head(5).to_markdown(index=True) + \
                                "\n\n" + Y_targets_train.head(5).to_markdown(index=True)   
    await create_markdown_artifact(
        key="processed-features-targets-sample",
        markdown=f"## Vorschau der Features (X) und Targets (Y) (erste 5 Zeilen)\n\n{processed_data_markdown}",
        description="Zeigt einen Ausschnitt der verarbeiteten Features und Targets."
    )

    # 3. Modell-Training
    # 3-1. Training vor Validierung (Daten der letzten 2 Tage werden zur Validierung im Anschluss vorhergesagt)
    first_model_training_futures = []
    print(f"Starte Training für {FORECAST_TIME_WINDOW} Horizonte...")

    for h in range(1, FORECAST_TIME_WINDOW + 1):
        target_column_name = f'target_temp_plus_{h}h'
        if target_column_name not in Y_targets_train.columns:
            print(f"WARNUNG: Zielspalte {target_column_name} nicht in Y_targets_train gefunden. Überspringe Horizont {h}.")
            continue
        
        y_h_train = Y_targets_train[target_column_name]

        future = train_single_model.submit(
            X_train_df=X_train, 
            y_train_series=y_h_train,
            horizon_hours=h,
            base_save_path=MODEL_PATH
        )
        first_model_training_futures.append(future)

    first_training_results = []
    first_training_models = {}
    for i, future in enumerate(first_model_training_futures):
        try:
            result, model = future.result()
            first_training_results.append(result)
            first_training_models[i + 1] = model
            print(f"Ergebnis für Horizont {result.get('horizon', i+1)} erhalten.")
        except Exception as e:
            print(f"FEHLER beim Abrufen des Ergebnisses für Future {i+1} (Horizont ~{i+1}): {e}")
            first_training_results.append({
                "horizon": i+1, # Platzhalter, falls Horizont nicht im Fehlerfall verfügbar
                "model_path": None,
                "rmse_fit": None,
                "n_samples_trained": 0, "error": str(e)
            })

    # 3-2. Vorhersage auf Validierungsdaten und erzeugen eines Plots (siehe Artifact im Subflow Run)
    await generate_validation_flow(
        X_val=X_val,
        y_val=y_val,
        trained_models=first_training_models
    )

    # 3-3. Training auf gesamtem Trainingssatz (für anschließendes Forecasting)
    second_model_training_futures = []
    print(f"Starte Training für {FORECAST_TIME_WINDOW} Horizonte...")

    for h in range(1, FORECAST_TIME_WINDOW + 1):
        target_column_name = f'target_temp_plus_{h}h'
        if target_column_name not in Y_targets.columns:
            print(f"WARNUNG: Zielspalte {target_column_name} nicht in Y_targets gefunden. Überspringe Horizont {h}.")
            continue
        
        y_h_train = Y_targets[target_column_name]

        future = train_single_model.submit(
            X_train_df=X, 
            y_train_series=y_h_train,
            horizon_hours=h,
            base_save_path=MODEL_PATH,
            return_model_object=False
        )
        second_model_training_futures.append(future)

    second_training_results = []
    for i, future in enumerate(second_model_training_futures):
        try:
            result = future.result() 
            second_training_results.append(result)
            print(f"Ergebnis für Horizont {result.get('horizon', i+1)} erhalten.")
        except Exception as e:
            print(f"FEHLER beim Abrufen des Ergebnisses für Future {i+1} (Horizont ~{i+1}): {e}")
            second_training_results.append({
                "horizon": i+1, # Platzhalter, falls Horizont nicht im Fehlerfall verfügbar
                "model_path": None,
                "rmse_fit": None,
                "n_samples_trained": 0, "error": str(e)
            })

    with get_db_session() as db:
        if db is None:
            logger.error("Konnte keine DB-Session erhalten. Kann Ergebnisse nicht speichern.")
            raise RuntimeError("DB Session nicht verfügbar.")

        for i, future in enumerate(second_model_training_futures):
            try:
                result = future.result() 
                
                _update_or_create_model_in_db(db, result, logger)
                
                second_training_results.append(result)
                logger.info(f"Ergebnis für Horizont {result.get('horizon_hours', i+1)} verarbeitet und in DB gespeichert.")

            except Exception as e:
                logger.error(f"FEHLER beim Abrufen/Speichern für Horizont ~{i+1}: {e}", exc_info=True)
                error_result = {"horizon_hours": i + 1, "error": str(e)}
                second_training_results.append(error_result)

    # 4. create artefact of training metrics
    print("Alle Trainings-Tasks abgeschlossen. Erstelle Metrik-Artefakt...")
    metrics_markdown = _create_beautiful_markdown(second_training_results, FORECAST_TIME_WINDOW)

    await create_markdown_artifact(
        key="model-training-metrics",
        markdown=metrics_markdown,
        description="Zusammenfassung der Trainingsmetriken für alle Vorhersagehorizonte."
    )
