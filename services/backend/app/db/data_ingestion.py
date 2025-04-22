# services/backend/app/db/data_ingestion.py (Korrigierte Version)

import sys
import os
import logging
from typing import Dict, Any

# --- Logger Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- PYTHONPATH Setup ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)
logger.info(f"Added project root to sys.path: {project_root}")

# --- Importiere Module ---
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session, attributes
    from sqlalchemy.exc import SQLAlchemyError
    import requests
    from datetime import datetime, timezone, timedelta

    from app.core.config import settings
    from app.models import sensor as sensor_model
    from app.crud import crud_sensor
    from app.schemas import sensor as sensor_schema
except ImportError as e:
    logger.error(f"Fehler beim Importieren von Modulen: {e}. Stellen Sie sicher, dass alle Abhängigkeiten installiert sind und PYTHONPATH korrekt ist.", exc_info=True)
    sys.exit(1)

# --- Datenbank Setup ---
try:
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Datenbank-Engine und SessionLocal erfolgreich erstellt.")
except Exception as e:
    logger.error(f"Fehler beim Erstellen der Datenbank-Engine: {e}", exc_info=True)
    sys.exit(1)

# --- Helper Funktion zum sicheren Parsen von Daten ---
def parse_api_datetime(date_str: str | None) -> datetime | None:
    """Versucht, einen ISO-String (mit Z) sicher in ein TZ-aware datetime zu parsen."""
    if not date_str:
        return None
    try:
        # Ersetze Z und füge explizit +00:00 hinzu, falls nötig
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        dt = datetime.fromisoformat(date_str)
        # Stelle sicher, dass es Timezone-aware ist (Standard ist UTC)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc) # Konvertiere sicherheitshalber nach UTC
    except (ValueError, TypeError):
        logger.warning(f"Konnte Datum '{date_str}' nicht parsen.")
        return None

# --- Hauptfunktion ---
def fetch_and_store_data():
    """Holt Metadaten einer Sensorbox, erstellt Box und Sensoren falls nötig,
       und holt dann iterativ Sensordaten ab."""

    db: Session = SessionLocal()
    box_id = settings.SENSOR_BOX_ID
    if not box_id:
        logger.error("FEHLER: SENSOR_BOX_ID ist nicht in der Konfiguration gesetzt!")
        db.close()
        return

    logger.info(f"--- Start: Datenabruf für Box ID: {box_id} ---")
    try:
      time_window_days = int(settings.FETCH_TIME_WINDOW_DAYS)
    except (AttributeError, ValueError, TypeError):
      logger.warning("FETCH_TIME_WINDOW_DAYS nicht (korrekt) in Settings gefunden, verwende Default: 2 Tage")
      time_window_days = 2
    time_window = timedelta(days=time_window_days)

    try:
        # === Schritt 1: Box Metadaten von API holen ===
        logger.info("Schritt 1: Hole Box Metadaten von OpenSenseMap API...")
        api_url_box = f"https://api.opensensemap.org/boxes/{box_id}"
        box_response = requests.get(api_url_box, timeout=30)
        box_response.raise_for_status()
        box_data: Dict[str, Any] = box_response.json()
        logger.info(f"Metadaten für Box '{box_data.get('name', box_id)}' erfolgreich geholt.")

        # === Schritt 2: Box und zugehörige Sensoren in DB prüfen/erstellen ===
        db_sensor_box = crud_sensor.sensor_box.get(db, id=box_id)
        new_box_processed = False

        if not db_sensor_box:
            logger.info(f"SensorBox '{box_id}' nicht in DB gefunden. Erstelle...")

            # --- KORRIGIERTE ERSTELLUNG DES PAYLOADS ---
            # Extrahiere erforderliche und optionale Felder explizit
            try:
                box_create_payload = {
                    "box_id": box_data['_id'], # ID aus API
                    "name": box_data['name'],  # Name ist erforderlich!
                    "exposure": box_data.get('exposure'), # Optional
                    "model": box_data.get('model'),       # Optional
                    "currentLocation": box_data.get('currentLocation'), # Optional
                    "lastMeasurementAt": parse_api_datetime(box_data.get('lastMeasurementAt')), # Optional, sicher parsen
                    "createdAt": parse_api_datetime(box_data.get('createdAt')) or datetime.now(timezone.utc), # Erforderlich, Fallback auf now()
                    "updatedAt": parse_api_datetime(box_data.get('updatedAt')) or datetime.now(timezone.utc)  # Erforderlich, Fallback auf now()
                    # last_data_fetched wird hier NICHT gesetzt, bleibt initial NULL
                }
                # Entferne Schlüssel mit None-Werten, falls das Schema das nicht mag (optional)
                # box_create_payload = {k: v for k, v in box_create_payload.items() if v is not None}

                sensor_box_schema_create = sensor_schema.SensorBoxCreate(**box_create_payload)

            except KeyError as e_key:
                 logger.error(f"Fehler: Erforderliches Feld '{e_key}' fehlt in API-Antwort für Box '{box_id}'. API-Daten: {box_data}")
                 db.rollback()
                 return
            except Exception as e_pydantic:
                 logger.error(f"Fehler bei Pydantic Validierung für SensorBoxCreate: {e_pydantic}", exc_info=True)
                 logger.error(f"Daten, die zum Fehler führten: {box_create_payload}")
                 db.rollback()
                 return
            # --- ENDE KORREKTUR ---

            db_sensor_box_obj = crud_sensor.sensor_box.create(db, obj_in=sensor_box_schema_create)
            logger.info(f"SensorBox '{box_id}' zur Session hinzugefügt.")

            # 2b. Zugehörige Sensoren erstellen (wie zuvor)
            if 'sensors' in box_data and isinstance(box_data['sensors'], list):
                logger.info(f"Erstelle zugehörige Sensoren für Box '{box_id}'...")
                sensor_creation_failed = False
                for api_sensor in box_data['sensors']:
                    try:
                        existing_sensor = crud_sensor.sensor.get(db=db, id=api_sensor['_id'])
                        if existing_sensor:
                             logger.info(f"  Sensor '{api_sensor['_id']}' existiert bereits.")
                             continue

                        # Annahme: SensorCreate Schema erwartet diese Felder
                        sensor_create_schema = sensor_schema.SensorCreate(
                            sensor_id=api_sensor['_id'],
                            title=api_sensor.get('title'),
                            unit=api_sensor.get('unit'),
                            sensor_type=api_sensor.get('sensorType'),
                            box_id=box_id
                        )
                        crud_sensor.sensor.create(db, obj_in=sensor_create_schema)
                        logger.info(f"  Sensor '{api_sensor['_id']}' zur Session hinzugefügt.")
                    except Exception as e_sensor:
                        logger.error(f"Fehler beim Erstellen von Sensor '{api_sensor.get('_id')}': {e_sensor}", exc_info=True)
                        sensor_creation_failed = True

                if sensor_creation_failed:
                     logger.error("Fehler beim Erstellen von Sensoren aufgetreten. Mache Rollback.")
                     db.rollback()
                     return
            else:
                logger.warning(f"Keine 'sensors'-Liste in API-Daten für Box '{box_id}' gefunden.")

            # 2c. Commit & Refresh (wie zuvor)
            try:
                logger.info("Committing new SensorBox and Sensors...")
                db.commit()
                logger.info("Commit erfolgreich.")
                db.refresh(db_sensor_box_obj, attribute_names=['sensors'])
                db_sensor_box = db_sensor_box_obj
                logger.info(f"SensorBox-Objekt aktualisiert. Geladene Sensoren: {len(db_sensor_box.sensors)}")
                new_box_processed = True
            except SQLAlchemyError as e_commit:
                logger.error(f"Datenbankfehler beim Commit: {e_commit}", exc_info=True)
                db.rollback()
                return

        else:
            logger.info(f"SensorBox '{box_id}' bereits in DB gefunden. Zugeordnete Sensoren: {len(db_sensor_box.sensors)}")
            # Optional: Hier Logik zur Synchronisation von Sensoren einfügen

        # === Schritt 3: lastMeasurementAt aktualisieren (wie zuvor) ===
        api_last_measurement_at = parse_api_datetime(box_data.get('lastMeasurementAt'))
        if api_last_measurement_at:
            db_last_measurement_at = db_sensor_box.lastMeasurementAt.astimezone(timezone.utc) if db_sensor_box.lastMeasurementAt else None
            api_last_measurement_at = api_last_measurement_at.astimezone(timezone.utc)

            if db_last_measurement_at is None or api_last_measurement_at > db_last_measurement_at:
                logger.info(f"Aktualisiere lastMeasurementAt für SensorBox '{box_id}' von {db_last_measurement_at} auf {api_last_measurement_at}.")
                db_sensor_box.lastMeasurementAt = api_last_measurement_at
                attributes.instance_state(db_sensor_box).modified = True

        # === Schritt 4: Zeitfenster für Datenabruf bestimmen (wie zuvor) ===
        now_utc = datetime.now(timezone.utc)
        to_date_utc = api_last_measurement_at if api_last_measurement_at else now_utc
        if to_date_utc > now_utc:
            to_date_utc = now_utc

        last_fetched_utc = db_sensor_box.last_data_fetched.astimezone(timezone.utc) if db_sensor_box.last_data_fetched else None
        created_at_utc = db_sensor_box.createdAt.astimezone(timezone.utc)

        # WICHTIG: Wenn die Box neu ist, MUSS createdAt als Start verwendet werden.
        # last_data_fetched ist hier noch NULL.
        current_from_date = created_at_utc if new_box_processed or last_fetched_utc is None else last_fetched_utc

        current_from_date = current_from_date.astimezone(timezone.utc)
        to_date_utc = to_date_utc.astimezone(timezone.utc)

        if current_from_date >= to_date_utc:
            logger.info(f"Daten für Box '{box_id}' scheinen aktuell (Start: {current_from_date}, Ende: {to_date_utc}). Kein Datenabruf nötig.")
            if db.is_modified(db_sensor_box):
                 logger.info("Committing Metadaten-Updates (lastMeasurementAt)...")
                 db.commit()
            db.close()
            return

        logger.info(f"Bestimmtes Abruffensfer für Box '{box_id}': FROM {current_from_date} TO {to_date_utc}")

        # === Schritt 5: Sensordaten iterativ abrufen (wie zuvor) ===
        successful_fetch_end_date = current_from_date
        fetch_errors_occurred = False

        if not db_sensor_box.sensors:
             logger.warning(f"Keine Sensoren für Box '{box_id}' in DB gefunden zum Datenabruf.")
        else:
            logger.info(f"Iteriere durch {len(db_sensor_box.sensors)} Sensoren...")

        for sensor in db_sensor_box.sensors:
            logger.info(f"--- Start Verarbeitung Sensor: {sensor.sensor_id} ('{sensor.title}') ---")
            sensor_loop_from_date = current_from_date

            while sensor_loop_from_date < to_date_utc:
                loop_to_date = sensor_loop_from_date + time_window
                if loop_to_date > to_date_utc:
                    loop_to_date = to_date_utc

                from_date_str = sensor_loop_from_date.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
                to_date_str = loop_to_date.isoformat(timespec='milliseconds').replace('+00:00', 'Z')

                api_url_data = f"https://api.opensensemap.org/boxes/{box_id}/data/{sensor.sensor_id}"
                params = {"from-date": from_date_str, "to-date": to_date_str, "format": "json"}
                logger.info(f"  API Request: Sensor '{sensor.sensor_id}', Von: {from_date_str}, Bis: {to_date_str}")

                try:
                    response = requests.get(api_url_data, params=params, timeout=45)
                    response.raise_for_status()
                    sensor_measurements = response.json()
                    logger.info(f"  API Antwort: {len(sensor_measurements)} Datenpunkte erhalten.")

                    if sensor_measurements:
                        all_sensor_data_schemas = []
                        batch_latest_ts = None
                        for measurement in sensor_measurements:
                            try:
                                ts = parse_api_datetime(measurement.get('createdAt'))
                                val_str = measurement.get('value')
                                if ts is None or val_str is None:
                                    logger.warning(f"  Überspringe Messwert wegen fehlendem Datum oder Wert: {measurement}")
                                    continue
                                val = float(val_str)

                                all_sensor_data_schemas.append(sensor_schema.SensorDataCreate(
                                    sensor_id=sensor.sensor_id,
                                    value=val,
                                    measurement_timestamp=ts
                                ))
                                batch_latest_ts = max(ts, batch_latest_ts) if batch_latest_ts else ts
                            except (ValueError, TypeError, KeyError) as e_meas:
                                logger.warning(f"  Überspringe ungültigen Messwert: {measurement}. Fehler: {e_meas}")
                                continue

                        if all_sensor_data_schemas:
                            crud_sensor.sensor_data.create_multi(db, objs_in=all_sensor_data_schemas)
                            logger.info(f"  {len(all_sensor_data_schemas)} Datenpunkte für Sensor '{sensor.sensor_id}' in Session gespeichert.")
                            if batch_latest_ts and batch_latest_ts > successful_fetch_end_date:
                                successful_fetch_end_date = batch_latest_ts

                except requests.exceptions.RequestException as e_req:
                    logger.error(f"  API Fehler für Sensor '{sensor.sensor_id}': {e_req}", exc_info=False)
                    fetch_errors_occurred = True
                    break
                except Exception as e_proc:
                    logger.error(f"  Verarbeitungsfehler für Sensor '{sensor.sensor_id}': {e_proc}", exc_info=True)
                    fetch_errors_occurred = True
                    break

                sensor_loop_from_date = loop_to_date

            logger.info(f"--- Ende Verarbeitung Sensor: {sensor.sensor_id} ---")

        # === Schritt 6: Finalen Status speichern (wie zuvor) ===
        if not fetch_errors_occurred:
            update_ts = to_date_utc
            logger.info(f"Alle Abrufe erfolgreich. Setze last_data_fetched auf: {update_ts}")
        else:
            update_ts = successful_fetch_end_date
            logger.warning(f"Fehler beim Abruf. Setze last_data_fetched nur auf letzten erfolgreichen Punkt: {update_ts}")

        update_ts = update_ts.astimezone(timezone.utc)
        previous_last_fetched = db_sensor_box.last_data_fetched.astimezone(timezone.utc) if db_sensor_box.last_data_fetched else None

        if previous_last_fetched is None or update_ts > previous_last_fetched:
             db_sensor_box.last_data_fetched = update_ts
             attributes.instance_state(db_sensor_box).modified = True
             logger.info(f"Aktualisiere last_data_fetched für Box '{box_id}' auf {update_ts}")
        else:
             logger.info(f"Kein Update für last_data_fetched nötig (Current: {previous_last_fetched}, Target: {update_ts})")

        if db.is_modified(db_sensor_box) or db.new or db.deleted:
            logger.info("Committing final state updates...")
            db.commit()
            logger.info("Final commit successful.")
        else:
            logger.info("No final state updates to commit.")


    except requests.exceptions.RequestException as e_box_fetch:
        logger.error(f"FATAL: Fehler beim Holen der Box-Metadaten: {e_box_fetch}", exc_info=True)
        db.rollback()
    except SQLAlchemyError as e_db:
        logger.error(f"FATAL: Datenbankfehler aufgetreten: {e_db}", exc_info=True)
        db.rollback()
    except Exception as e_main:
        logger.error(f"FATAL: Ein unerwarteter Fehler ist aufgetreten: {e_main}", exc_info=True)
        db.rollback()
    finally:
        logger.info(f"--- Ende: Datenabrufversuch für Box ID: {box_id} ---")
        db.close()

# --- Skriptausführung ---
if __name__ == "__main__":
    logger.info("=================================================")
    logger.info("Standalone Script Execution: Fetch and Store Data")
    logger.info("=================================================")
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    loaded = load_dotenv(dotenv_path=dotenv_path)
    if loaded:
        logger.info(f"Umgebungsvariablen aus '{dotenv_path}' geladen.")
    else:
        logger.warning(f"Keine .env Datei unter '{dotenv_path}' gefunden oder konnte nicht geladen werden.")
        if not os.getenv("DATABASE_URL"):
             logger.error("FEHLER: DATABASE_URL nicht gefunden.")
             sys.exit(1)
        if not os.getenv("SENSOR_BOX_ID"):
             logger.error("FEHLER: SENSOR_BOX_ID nicht gefunden.")
             sys.exit(1)

    fetch_and_store_data()
    logger.info("Script finished.")