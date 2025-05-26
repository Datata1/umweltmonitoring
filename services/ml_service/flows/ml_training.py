import os
import sys
import pandas as pd
from pathlib import Path

from prefect import flow, task
from prefect_dask.task_runners import DaskTaskRunner
from prefect.futures import PrefectFuture
from prefect.artifacts import create_markdown_artifact 


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tasks.fetch_data import fetch_sensor_data_for_ml
from tasks.data_transformations import create_ml_features
from tasks.ml_training import train_single_model
from utils.config import settings

FORECAST_TIME_WINDOW = 48  # Stunden in die Zukunft

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

    # 1. get data from sensors
    sensor_data= fetch_sensor_data_for_ml(weeks=8)

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

    X = features_dict["X"]
    Y_targets = features_dict["Y_targets"]
    
    processed_data_markdown =   X.head(5).to_markdown(index=True) + \
                                "\n\n" + Y_targets.head(5).to_markdown(index=True)   
    await create_markdown_artifact(
        key="processed-features-targets-sample",
        markdown=f"## Vorschau der Features (X) und Targets (Y) (erste 5 Zeilen)\n\n{processed_data_markdown}",
        description="Zeigt einen Ausschnitt der verarbeiteten Features und Targets."
    )

    model_training_futures = []
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
            base_save_path=MODEL_PATH
        )
        model_training_futures.append(future)

    training_results = []
    for i, future in enumerate(model_training_futures):
        try:
            result = future.result() 
            training_results.append(result)
            print(f"Ergebnis für Horizont {result.get('horizon', i+1)} erhalten.")
        except Exception as e:
            print(f"FEHLER beim Abrufen des Ergebnisses für Future {i+1} (Horizont ~{i+1}): {e}")
            training_results.append({
                "horizon": i+1, # Platzhalter, falls Horizont nicht im Fehlerfall verfügbar
                "model_path": None, "rmse_fit": None, "mae_fit": None, "n_samples_trained": 0, "error": str(e)
            })

    # 4. create artefact of training metrics
    print("Alle Trainings-Tasks abgeschlossen. Erstelle Metrik-Artefakt...")
    if training_results:
        metrics_df = pd.DataFrame(training_results)
        metrics_df.sort_values(by="horizon", inplace=True)
        
        metrics_markdown = "## Trainingsmetriken der Modelle\n\n" + metrics_df.to_markdown(index=False)
        
        successful_trainings = metrics_df['error'].isnull().sum()
        failed_trainings = metrics_df['error'].notnull().sum()
        summary_text = (
            f"\n\n**Zusammenfassung:**\n"
            f"- Erfolgreich trainierte Modelle: {successful_trainings} von {FORECAST_TIME_WINDOW}\n"
            f"- Fehlgeschlagene Trainings: {failed_trainings}\n"
        )
        if failed_trainings > 0:
            summary_text += "- Details zu Fehlern siehe oben oder in den einzelnen Task-Logs.\n"

        metrics_markdown += summary_text

    else:
        metrics_markdown = "## Trainingsmetriken der Modelle\n\nKeine Trainingsergebnisse vorhanden."

    await create_markdown_artifact(
        key="model-training-metrics",
        markdown=metrics_markdown,
        description="Zusammenfassung der Trainingsmetriken für alle Vorhersagehorizonte."
    )