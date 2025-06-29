import os
import sys
import requests
from typing import List
from datetime import timedelta
from prefect import flow, get_run_logger
from prefect.artifacts import create_markdown_artifact
from prefect_dask.task_runners import DaskTaskRunner
from prefect.futures import PrefectFuture


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flows.ml_training import train_all_models
from tasks.fetch_data import fetch_box_metadata, fetch_store_sensor_chunk
from tasks.persist_in_db import sync_box_and_sensors_in_db, update_final_box_status
from utils.fetch_window import determine_fetch_window
from utils.config import settings

def is_database_empty(backend_url: str = "http://backend:8000") -> bool:
    """
    Checks if the database is empty by querying the /sensor_boxes endpoint.
    Returns True if no sensor boxes are found, False otherwise.
    """
    try:
        response = requests.get(f"{backend_url}/api/v1/sensor/5faeb5589b2df8001b980304/data")
        response.raise_for_status()  
        
        return not response.json()
        
    except requests.exceptions.RequestException as e:

        print(f"Error checking database status: {e}. Assuming database is not empty.")
        return False


@flow(
        log_prints=True,
        task_runner=DaskTaskRunner()
      )
async def data_ingestion_flow(
    box_id: str,
    initial_fetch_days: int = 365,
    fetch_chunk_days: int = 4,
    initial: bool = False
):

    logger = get_run_logger()

    # 1. Metadaten holen
    metadata = fetch_box_metadata(box_id)
    api_last_measurement_str = metadata.get('lastMeasurementAt') 

    # 2. Box & Sensoren in DB synchronisieren, DB-Status holen
    db_box_state, is_new_box = sync_box_and_sensors_in_db(metadata, initial_fetch_days)
    print("Box ist neu erstellt:", is_new_box)

    is_newly_created = db_box_state.get('is_newly_created', False)
    logger.info(f"Box {box_id} {'neu erstellt' if is_newly_created else 'aktualisiert'} in der Datenbank.")

    # 3. Abruf-Zeitfenster bestimmen
    from_date, to_date = determine_fetch_window(db_box_state, api_last_measurement_str)

    if from_date is None or to_date is None or from_date >= to_date:
        logger.info("Kein Datenabruf nötig, Daten sind aktuell.")
        return 

    # 4. Daten für jeden Sensor holen (Potenziell parallel)
    all_fetch_results = []
    sensor_ids = db_box_state.get("sensor_ids", [])

    if not sensor_ids:
         logger.warning(f"Keine Sensor-IDs für Box {box_id} gefunden.")
         return

    # --- Iteration über die Zeit in Chunks ---
    current_chunk_start = from_date
    while current_chunk_start < to_date:
        current_chunk_end = min(current_chunk_start + timedelta(days=fetch_chunk_days), to_date)
        logger.info(f"Bearbeite Zeit-Chunk: {current_chunk_start} -> {current_chunk_end}")

        chunk_futures: List[PrefectFuture] = fetch_store_sensor_chunk.map(
            sensor_id=sensor_ids,             
            box_id=box_id,                  
            chunk_from_date=current_chunk_start, 
            chunk_to_date=current_chunk_end   
        )

        chunk_results = chunk_futures.result() 
        all_fetch_results.extend(chunk_results)

        if not all(res.get('success', False) for res in chunk_results): 
             logger.error(f"Fehler im Zeit-Chunk {current_chunk_start} -> {current_chunk_end}. Breche weitere Chunks ab.")
             break 

        current_chunk_start = current_chunk_end # Gehe zum nächsten Chunk

    # 5. Finalen Box-Status (last_data_fetched) aktualisieren
    update_final_box_status(box_id, to_date, all_fetch_results) 

    logger.info(f"Flow für Box {box_id} abgeschlossen.") 

    if is_new_box:
        logger.info(f"Starte Modelltraining für Box {box_id}...")

        # 6. Modelle trainieren
        training_results = await train_all_models()

        logger.info(f"Modelltraining für Box {box_id} abgeschlossen. Ergebnisse: {training_results}")


