from prefect import task,  get_run_logger

from prefect import task, get_run_logger
from sqlalchemy.orm import Session, attributes 
from sqlalchemy.exc import SQLAlchemyError    
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone

from utils.db_utils import get_db_session

from shared.crud import crud_sensor
from shared.schemas import sensor as sensor_schema
from utils.parse_datetime import parse_api_datetime 


@task(
    name="Sync Box and Sensors in DB",
    log_prints=True
)
def sync_box_and_sensors_in_db(box_metadata: Dict[str, Any], initial_fetch_days: int) -> Dict[str, Any]:
    """
    Synchronisiert die Sensorbox und ihre Sensoren mit der Datenbank.
    """
    logger = get_run_logger()
    box_id = box_metadata.get('_id')

    if not box_id:
        logger.error("Box ID fehlt in den übergebenen Metadaten!")
        raise ValueError("Box ID fehlt in den Metadaten für DB Sync.")

    # Nutze den DB Session Context Manager
    with get_db_session() as db:
        if db is None:
            logger.error("Konnte keine DB-Session für sync_box_and_sensors_in_db erhalten.")
            raise RuntimeError("DB Session nicht verfügbar für Sync.")

        logger.info(f"[DB Sync] Starte Sync für Box: {box_id}")

        try:
            # === Schritt 1: Box holen oder erstellen ===
            db_sensor_box = crud_sensor.sensor_box.get(db, id=box_id)
            is_new_box = False

            if not db_sensor_box:
                is_new_box = True
                logger.info(f"[DB Sync] SensorBox '{box_id}' nicht gefunden. Erstelle...")

                # Berechne initiales last_data_fetched nur für neue Boxen
                api_last_measurement = parse_api_datetime(box_metadata.get('lastMeasurementAt'))
                calculated_last_fetched = None
                if api_last_measurement:
                     calculated_last_fetched = api_last_measurement - timedelta(days=initial_fetch_days)
                     logger.info(f"[DB Sync] Berechnetes initiales 'last_data_fetched': {calculated_last_fetched}")
                else:
                     logger.warning(f"[DB Sync] 'lastMeasurementAt' fehlt für initiale 'last_data_fetched'-Berechnung. Setze auf None.")

                # Erstelle Box-Payload und validiere mit Pydantic Schema
                try:
                    box_create_payload = {
                        "box_id": box_metadata['_id'],
                        "name": box_metadata['name'], 
                        "exposure": box_metadata.get('exposure'),
                        "model": box_metadata.get('model'),
                        "currentLocation": box_metadata.get('currentLocation'),
                        "lastMeasurementAt": api_last_measurement, 
                        "last_data_fetched": calculated_last_fetched, 
                        "createdAt": parse_api_datetime(box_metadata.get('createdAt')) or datetime.now(timezone.utc),
                        "updatedAt": parse_api_datetime(box_metadata.get('updatedAt')) or datetime.now(timezone.utc)
                    }
                    sensor_box_schema_create = sensor_schema.SensorBoxCreate(**box_create_payload)
                except KeyError as e:
                    logger.error(f"[DB Sync] Fehlendes Pflichtfeld '{e}' in API Metadaten für Box Erstellung.")
                    raise ValueError(f"Fehlendes Pflichtfeld '{e}' für Box {box_id}") from e
                except Exception as e_val: 
                     logger.error(f"[DB Sync] Validierungsfehler beim Erstellen des Box Payloads: {e_val}", exc_info=True)
                     raise ValueError(f"Payload Validierungsfehler für Box {box_id}") from e_val

                # Erstelle Box-Objekt in der DB-Session
                db_sensor_box = crud_sensor.sensor_box.create(db, obj_in=sensor_box_schema_create)
                logger.info(f"[DB Sync] SensorBox '{box_id}' zur Session hinzugefügt.")
                # Flush ist nötig, damit die Box (und ihre ID) in der Session bekannt ist,
                # bevor wir versuchen, Sensoren damit zu verknüpfen.
                db.flush()
                db.refresh(db_sensor_box)

            else:
                logger.info(f"[DB Sync] SensorBox '{box_id}' bereits in DB gefunden.")

            # === Schritt 2: Zugehörige Sensoren holen oder erstellen ===
            if not db_sensor_box:
                 logger.critical(f"[DB Sync] Interner Fehler: db_sensor_box ist None nach Get/Create für Box {box_id}.")
                 raise RuntimeError(f"Konnte SensorBox Objekt für {box_id} nicht laden/erstellen.")

            existing_sensor_ids = {s.sensor_id for s in db_sensor_box.sensors}
            logger.info(f"[DB Sync] Aktuell {len(existing_sensor_ids)} Sensoren für Box {box_id} in DB bekannt.")

            api_sensors = box_metadata.get('sensors', [])
            sensors_created_count = 0
            if isinstance(api_sensors, list):
                logger.info(f"[DB Sync] Verarbeite {len(api_sensors)} Sensoren aus API-Metadaten...")
                for api_sensor in api_sensors:
                    api_sensor_id = api_sensor.get('_id')
                    if not api_sensor_id:
                        logger.warning(f"[DB Sync] Überspringe Sensor ohne '_id' in Metadaten: {api_sensor}")
                        continue

                    # Prüfen, ob der Sensor bereits existiert
                    if api_sensor_id not in existing_sensor_ids:
                         logger.info(f"[DB Sync] Erstelle Sensor '{api_sensor_id}' für Box '{box_id}'...")
                         try:
                             sensor_create_schema = sensor_schema.SensorCreate(
                                 sensor_id=api_sensor_id,
                                 title=api_sensor.get('title'),
                                 unit=api_sensor.get('unit'),
                                 sensor_type=api_sensor.get('sensorType'),
                                 box_id=box_id # Verknüpfung zur Box
                             )
                             crud_sensor.sensor.create(db, obj_in=sensor_create_schema)
                             sensors_created_count += 1
                         except Exception as e_sensor:
                             logger.error(f"[DB Sync] Fehler beim Erstellen von Sensor '{api_sensor_id}': {e_sensor}", exc_info=True)


                if sensors_created_count > 0:
                     logger.info(f"[DB Sync] {sensors_created_count} neue Sensoren zur Session hinzugefügt.")
                     # Flush erneut, um neue Sensoren in der Session verfügbar zu machen
                     db.flush()
                     # Lade die 'sensors'-Beziehung neu, um die neuen Sensoren zu inkludieren
                     db.refresh(db_sensor_box, attribute_names=['sensors'])
            else:
                 logger.warning(f"[DB Sync] Keine gültige 'sensors'-Liste in API-Daten für Box '{box_id}' gefunden.")

            # === Schritt 3: lastMeasurementAt aktualisieren ===
            api_last_measurement_at_dt = parse_api_datetime(box_metadata.get('lastMeasurementAt'))
            if api_last_measurement_at_dt:
                db_last_measurement_at_dt = db_sensor_box.lastMeasurementAt.astimezone(timezone.utc) if db_sensor_box.lastMeasurementAt else None
                api_last_measurement_at_dt = api_last_measurement_at_dt.astimezone(timezone.utc)

                if db_last_measurement_at_dt is None or api_last_measurement_at_dt > db_last_measurement_at_dt:
                    logger.info(f"[DB Sync] Aktualisiere lastMeasurementAt für Box '{box_id}' von {db_last_measurement_at_dt} auf {api_last_measurement_at_dt}.")
                    db_sensor_box.lastMeasurementAt = api_last_measurement_at_dt
                else:
                     logger.info(f"[DB Sync] DB.lastMeasurementAt ({db_last_measurement_at_dt}) ist aktuell.")

            # === Schritt 4: Rückgabewert vorbereiten ===
            final_sensor_ids = [s.sensor_id for s in db_sensor_box.sensors]
            db_state_to_return = {
                "box_id": db_sensor_box.box_id,
                "db_last_measurement_at": db_sensor_box.lastMeasurementAt.astimezone(timezone.utc) if db_sensor_box.lastMeasurementAt else None,
                "db_last_data_fetched": db_sensor_box.last_data_fetched.astimezone(timezone.utc) if db_sensor_box.last_data_fetched else None,
                "sensor_ids": final_sensor_ids
            }
            logger.info(f"[DB Sync] Vorbereiteter Rückgabestatus: {db_state_to_return}")

        except SQLAlchemyError as e_db:
            logger.error(f"[DB Sync] Datenbankfehler während Sync für Box {box_id}: {e_db}", exc_info=True)
            raise 
        except Exception as e_sync:
            logger.error(f"[DB Sync] Unerwarteter Fehler während Sync für Box {box_id}: {e_sync}", exc_info=True)
            raise 

    logger.info(f"[DB Sync] Sync-Task für Box {box_id} abgeschlossen.")
    return db_state_to_return 



@task(
    name="Update Final Box Status",
    log_prints=True
)
def update_final_box_status(
    box_id: str,
    overall_to_date: datetime, 
    fetch_results: List[Dict[str, Any]] 
) -> None:
    """
    Aktualisiert den 'last_data_fetched'-Zeitstempel für die SensorBox in der DB,
    basierend auf den Ergebnissen der einzelnen Fetch-Chunks.
    """
    logger = get_run_logger()

    if not fetch_results:
        logger.warning(f"[Final Status {box_id}] Keine Fetch-Ergebnisse erhalten. Überspringe Update.")
        return

    overall_success = all(res.get('success', False) for res in fetch_results)
    latest_successful_ts: datetime | None = None

    for res in fetch_results:
        if res.get('success') and res.get('last_timestamp_in_chunk'):
            ts = res['last_timestamp_in_chunk']
            if isinstance(ts, datetime):
                ts_utc = ts.astimezone(timezone.utc)
                if latest_successful_ts is None or ts_utc > latest_successful_ts:
                    latest_successful_ts = ts_utc
            else:
                logger.warning(f"[Final Status {box_id}] Ungültiger Typ für 'last_timestamp_in_chunk' in Ergebnis: {res}")


    logger.info(f"[Final Status {box_id}] Gesamt-Erfolg der Chunks: {overall_success}")
    logger.info(f"[Final Status {box_id}] Spätester erfolgreicher Zeitstempel: {latest_successful_ts}")

    update_ts: datetime | None = None

    with get_db_session() as db:
        if db is None:
            logger.error("Konnte keine DB-Session für update_final_box_status erhalten.")
            raise RuntimeError("DB Session nicht verfügbar für finales Update.")

        try:
            db_sensor_box = crud_sensor.sensor_box.get(db, id=box_id)
            if not db_sensor_box:
                logger.error(f"[Final Status {box_id}] SensorBox nicht in DB gefunden!")
                # Hier kann man nicht viel tun, vielleicht den Fehler loggen und beenden
                return 

            previous_last_fetched = db_sensor_box.last_data_fetched.astimezone(timezone.utc) if db_sensor_box.last_data_fetched else None
            logger.info(f"[Final Status {box_id}] Vorheriger 'last_data_fetched': {previous_last_fetched}")

            if overall_success:
                update_ts = overall_to_date.astimezone(timezone.utc)
                logger.info(f"[Final Status {box_id}] Setze 'last_data_fetched' auf Ziel-Enddatum: {update_ts}")
            else:
                if latest_successful_ts:
                     start_point = previous_last_fetched if previous_last_fetched else datetime.min.replace(tzinfo=timezone.utc)
                     update_ts = max(start_point, latest_successful_ts)
                     logger.warning(f"[Final Status {box_id}] Fehler aufgetreten. Setze 'last_data_fetched' auf max(alt, letzter Erfolg): {update_ts}")
                else:
                     update_ts = previous_last_fetched
                     logger.warning(f"[Final Status {box_id}] Fehler aufgetreten und kein späterer erfolgreicher Punkt gefunden. 'last_data_fetched' bleibt: {update_ts}")

            if update_ts and (previous_last_fetched is None or update_ts > previous_last_fetched):
                logger.info(f"[Final Status {box_id}] Aktualisiere 'last_data_fetched' in DB auf {update_ts}")
                db_sensor_box.last_data_fetched = update_ts
            elif update_ts is not None:
                logger.info(f"[Final Status {box_id}] Kein Update für 'last_data_fetched' nötig (Neuer Wert {update_ts} nicht später als alter Wert {previous_last_fetched}).")
            else:
                 logger.info(f"[Final Status {box_id}] Kein gültiger Update-Zeitstempel ermittelt. 'last_data_fetched' wird nicht geändert.")

        except SQLAlchemyError as e_db:
            logger.error(f"[Final Status {box_id}] Datenbankfehler während Update: {e_db}", exc_info=True)
            raise 
        except Exception as e_final:
            logger.error(f"[Final Status {box_id}] Unerwarteter Fehler während Update: {e_final}", exc_info=True)
            raise 

    logger.info(f"[Final Status {box_id}] Update-Task abgeschlossen.")
