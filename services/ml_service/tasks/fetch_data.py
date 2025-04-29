# tasks/fetch_data.py

import requests
from typing import Dict, Any, List 
from prefect import task, get_run_logger
from datetime import datetime, timezone, timedelta 
from sqlalchemy.exc import SQLAlchemyError 

from utils.db_utils import get_db_session

from shared.crud import crud_sensor
from shared.schemas import sensor as sensor_schema
from utils.parse_datetime import parse_api_datetime

OPEN_SENSE_MAP_API_URL = "https://api.opensensemap.org"

@task(
    name="Fetch OpenSenseMap Box Metadata", 
    retries=3,                             
    retry_delay_seconds=10,               
    log_prints=True                        
)
def fetch_box_metadata(box_id: str) -> Dict[str, Any]:
    """
    Holt Metadaten für eine spezifische Sensorbox von der OpenSenseMap API.
    """
    logger = get_run_logger()

    if not box_id:
        logger.error("Keine Box ID für den Metadatenabruf übergeben!")
        raise ValueError("box_id darf nicht leer sein.")

    api_url = f"{OPEN_SENSE_MAP_API_URL}/boxes/{box_id}"
    logger.info(f"Hole Metadaten für Box ID: {box_id} von API: {api_url}")

    try:
        response = requests.get(api_url, timeout=30) 

        response.raise_for_status()

        box_data = response.json()
        logger.info(f"Metadaten für Box '{box_data.get('name', box_id)}' erfolgreich geholt.")
        return box_data

    # --- Spezifischere Fehlerbehandlung für bessere Logs ---
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP Fehler beim Abruf von Box {box_id}: Status {http_err.response.status_code}")
        try:
            logger.error(f"API Fehlerantwort (Auszug): {http_err.response.text[:500]}...")
        except Exception:
            pass 
        raise http_err from http_err
    except requests.exceptions.ConnectionError as conn_err:
         logger.error(f"Verbindungsfehler beim Abruf von Box {box_id}: {conn_err}")
         raise conn_err from conn_err
    except requests.exceptions.Timeout as timeout_err:
         logger.error(f"Timeout beim Abruf von Box {box_id}: {timeout_err}")
         raise timeout_err from timeout_err
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Allgemeiner Request-Fehler beim Abruf von Box {box_id}: {req_err}")
        raise req_err from req_err
    except requests.exceptions.JSONDecodeError as json_err:
         logger.error(f"Fehler beim Parsen der JSON-Antwort für Box {box_id}: {json_err}")
         try:
              logger.error(f"Empfangener Text (Auszug): {response.text[:500]}...")
         except NameError: 
              pass
         raise ValueError(f"Ungültige JSON-Antwort von API für Box {box_id}") from json_err


@task(
    name="Fetch and Store Sensor Chunk",
    retries=2,                 
    retry_delay_seconds=15,     
    log_prints=True
)
def fetch_store_sensor_chunk(
    sensor_id: str,
    box_id: str,
    chunk_from_date: datetime,
    chunk_to_date: datetime
) -> Dict[str, Any]:
    """
    Holt, parst und speichert Messdaten für einen Sensor in einem Zeit-Chunk.
    """
    logger = get_run_logger()
    result = {
        "sensor_id": sensor_id,
        "chunk_from": chunk_from_date,
        "chunk_to": chunk_to_date,
        "success": False,
        "points_fetched": 0,
        "last_timestamp_in_chunk": None 
    }

    # Stelle sicher, dass Datumsangaben Timezone-aware sind und formatiere für API
    try:
        from_date_str = chunk_from_date.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        to_date_str = chunk_to_date.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    except AttributeError:
        logger.error(f"[Chunk {sensor_id}] Ungültige Datums-Objekte empfangen: From={chunk_from_date}, To={chunk_to_date}")
        return result 

    api_url = f"{OPEN_SENSE_MAP_API_URL}/boxes/{box_id}/data/{sensor_id}"
    params = {"from-date": from_date_str, "to-date": to_date_str, "format": "json"}
    logger.info(f"[Chunk {sensor_id}] API Request: Von {from_date_str} Bis {to_date_str}")

    all_sensor_data_schemas: List[sensor_schema.SensorDataCreate] = []
    batch_latest_ts: datetime | None = None

    try:
        # === Schritt 1: API-Aufruf ===
        response = requests.get(api_url, params=params, timeout=60)
        response.raise_for_status() 
        sensor_measurements = response.json()
        logger.info(f"[Chunk {sensor_id}] API Antwort: {len(sensor_measurements)} Punkte erhalten.")

        # === Schritt 2: Daten parsen und validieren ===
        if sensor_measurements:
            for measurement in sensor_measurements:
                try:
                    ts = parse_api_datetime(measurement.get('createdAt'))
                    val_str = measurement.get('value')

                    if ts is None or val_str is None:
                        logger.warning(f"[Chunk {sensor_id}] Überspringe Messwert wegen fehlendem Datum/Wert: {measurement}")
                        continue

                    # Konvertiere Wert zu float
                    val = float(val_str)

                    # Stelle sicher, dass Zeitstempel UTC ist
                    ts_utc = ts.astimezone(timezone.utc)

                    # Erstelle Pydantic Schema für DB-Einfügung
                    all_sensor_data_schemas.append(sensor_schema.SensorDataCreate(
                        sensor_id=sensor_id, 
                        value=val,
                        measurement_timestamp=ts_utc 
                    ))

                    # Merke dir den letzten Zeitstempel dieses Chunks
                    if batch_latest_ts is None or ts_utc > batch_latest_ts:
                        batch_latest_ts = ts_utc

                except (ValueError, TypeError, KeyError) as e_meas:
                    logger.warning(f"[Chunk {sensor_id}] Überspringe ungültigen Messwert: {measurement}. Fehler: {e_meas}")
                    continue

            # === Schritt 3: Daten in DB speichern (wenn vorhanden) ===
            if all_sensor_data_schemas:
                with get_db_session() as db:
                    if db is None:
                        logger.error(f"[Chunk {sensor_id}] Konnte keine DB-Session zum Speichern erhalten.")
                        raise RuntimeError("DB Session nicht verfügbar zum Speichern.")

                    try:
                        # Nutze die Bulk-Insert Funktion
                        crud_sensor.sensor_data.create_multi(db, objs_in=all_sensor_data_schemas)
                        logger.info(f"[Chunk {sensor_id}] {len(all_sensor_data_schemas)} Datenpunkte erfolgreich in DB gespeichert.")
                        result["points_fetched"] = len(all_sensor_data_schemas)
                        result["last_timestamp_in_chunk"] = batch_latest_ts
                        result["success"] = True
                    except SQLAlchemyError as e_db:
                        logger.error(f"[Chunk {sensor_id}] DB Fehler beim Speichern von {len(all_sensor_data_schemas)} Punkten: {e_db}", exc_info=True)
                        raise 
                    except Exception as e_crud:
                         logger.error(f"[Chunk {sensor_id}] Unerwarteter Fehler in create_multi: {e_crud}", exc_info=True)
                         raise 
            else:
                 logger.info(f"[Chunk {sensor_id}] Keine gültigen Messwerte in diesem Chunk gefunden/empfangen.")
                 result["success"] = True

        # === Schritt 4: Fehlerbehandlung für API-Call / Allgemeine Fehler ===
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"[Chunk {sensor_id}] HTTP Fehler: Status {http_err.response.status_code}")
        try: logger.error(f"API Fehlerantwort (Auszug): {http_err.response.text[:500]}...")
        except Exception: pass
        raise http_err
    except requests.exceptions.RequestException as req_err:
        logger.error(f"[Chunk {sensor_id}] Request Fehler: {req_err}")
        raise req_err 
    except ValueError as val_err: 
         logger.error(f"[Chunk {sensor_id}] Daten-Validierungsfehler: {val_err}", exc_info=True)
         raise val_err #
    except Exception as e_gen:
        logger.error(f"[Chunk {sensor_id}] Unerwarteter Fehler im Task: {e_gen}", exc_info=True)
        raise e_gen #

    logger.info(f"[Chunk {sensor_id}] Task beendet mit Erfolg: {result['success']}")
    return result 