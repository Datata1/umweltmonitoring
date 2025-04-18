import sys
import os
import logging

logger = logging.getLogger(__name__)

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
app_dir = os.path.dirname(parent_dir)
sys.path.append(app_dir)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import requests
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.models import sensor as sensor_model
from app.crud import crud_sensor
from app.schemas import sensor as sensor_schema

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def fetch_and_store_data():
    db = SessionLocal()
    box_id = settings.SENSOR_BOX_ID
    time_window = timedelta(days=2)  # Festes Zeitfenster von 2 Tagen
    try:
        api_url_box = f"https://api.opensensemap.org/boxes/{box_id}"
        box_response = requests.get(api_url_box)
        box_response.raise_for_status()
        box_data = box_response.json()

        # Überprüfe, ob die SensorBox bereits existiert
        db_sensor_box = crud_sensor.sensor_box.get(db, id=box_id)

        # Erstelle die SensorBox, falls sie nicht existiert
        if not db_sensor_box:
            sensor_box_schema_create = sensor_schema.SensorBoxCreate(box_id=box_data['_id'], **box_data)
            db_sensor_box = crud_sensor.sensor_box.create(db, obj_in=sensor_box_schema_create)
            logger.info(f"Sensorbox mit ID '{box_id}' erfolgreich erstellt.")
        else:
            logger.info(f"Sensorbox mit ID '{box_id}' gefunden.")

        api_last_measurement_at_str = box_data.get('lastMeasurementAt')
        if api_last_measurement_at_str:
            api_last_measurement_at = datetime.fromisoformat(api_last_measurement_at_str.replace('Z', '+00:00'))
            # Nur aktualisieren, wenn der API-Wert neuer ist
            if db_sensor_box.lastMeasurementAt is None or api_last_measurement_at > db_sensor_box.lastMeasurementAt:
                 db_sensor_box.lastMeasurementAt = api_last_measurement_at
                 # todo? Aktualisiere auch andere Felder der Box, wenn nötig
                 db.add(db_sensor_box)
                 db.commit()
                 logger.info(f"lastMeasurementAt für Sensorbox '{box_id}' auf {api_last_measurement_at} aktualisiert.")

        now = datetime.now(timezone.utc)

        # Bestimme den globalen Endzeitpunkt für die Datenabfrage (basierend auf lastMeasurementAt)
        to_date = db_sensor_box.lastMeasurementAt if db_sensor_box.lastMeasurementAt else now
        if to_date > now:
            to_date = now

        # Iteriere durch alle Sensoren der SensorBox und rufe die Daten ab
        for sensor in db_sensor_box.sensors:
            logger.info(f"Fetching data for sensor: {sensor.sensor_id}")
            # Bestimme den Startzeitpunkt für diesen spezifischen Sensor
            if db_sensor_box.last_data_fetched:
                current_from_date = db_sensor_box.last_data_fetched
            else:
                current_from_date = db_sensor_box.createdAt

            # **Konvertiere current_from_date hier explizit nach UTC**
            current_from_date = current_from_date.astimezone(timezone.utc)

            # **Konvertiere to_date hier explizit nach UTC**
            to_date_utc = to_date.astimezone(timezone.utc)


            if current_from_date >= to_date_utc:
                 logger.info(f"  Data for sensor '{sensor.sensor_id}' is up to date.")
                 continue # Gehe zum nächsten Sensor

            logger.info(f"  Initial current_from_date (UTC): {current_from_date}")
            logger.info(f"  Fetching up to to_date (UTC): {to_date_utc}")

            while current_from_date < to_date_utc:
                next_to_date = current_from_date + time_window
                if next_to_date > to_date_utc:
                    next_to_date = to_date_utc

                # **Formatierung nach expliziter UTC-Konvertierung**
                from_date_str = current_from_date.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
                to_date_str = next_to_date.isoformat(timespec='milliseconds').replace('+00:00', 'Z')

                api_url = f"https://api.opensensemap.org/boxes/{box_id}/data/{sensor.sensor_id}"
                logger.info(f"  API URL: {api_url}")
                params = {
                    "from-date": from_date_str,
                    "to-date": to_date_str,
                    "format": "json"
                }
                logger.info(f"  Requesting data from: {from_date_str} to {to_date_str}")
                response = requests.get(api_url, params=params)
                response.raise_for_status()
                sensor_measurements = response.json()
                logger.info(f"  Received {len(sensor_measurements)} data points.")
                # logger.info(f"  Data from {from_date_str} to {to_date_str}: {sensor_measurements}") # Kommentiere diese Zeile aus, da sie sehr viel Ausgabe erzeugen kann


                if not sensor_measurements:
                    logger.info("  No data in this time window.")

                all_sensor_data = []
                for measurement in sensor_measurements:
                    measurement_timestamp = datetime.fromisoformat(measurement['createdAt'].replace('Z', '+00:00'))
                    sensor_data_schema_create = sensor_schema.SensorDataCreate(
                        sensor_id=sensor.sensor_id,
                        value=float(measurement['value']),
                        measurement_timestamp=measurement_timestamp
                    )
                    all_sensor_data.append(sensor_data_schema_create)

                if all_sensor_data:
                    crud_sensor.sensor_data.create_multi(db, objs_in=all_sensor_data)
                    logger.info(f"  Saved {len(all_sensor_data)} data points for sensor '{sensor.sensor_id}'.")

                current_from_date = next_to_date

        # Aktualisiere den last_data_fetched Zeitpunkt der SensorBox auf den Endzeitpunkt der gesamten Abfrage
        db_sensor_box.last_data_fetched = to_date # to_date ist der Endpunkt der gesamten Datenabfrage (im richtigen Zeitzonenformat)
        crud_sensor.sensor_box.update(db, db_obj=db_sensor_box, obj_in=sensor_schema.SensorBoxUpdate.model_validate(db_sensor_box))
        db.commit()

    except requests.exceptions.RequestException as e:
        db.rollback()
        logger.error(f"Fehler beim Abrufen der Daten von der OpenSenseMap API: {e}", exc_info=True)
    except Exception as e:
        db.rollback()
        logger.error(f"Ein Fehler ist aufgetreten: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    fetch_and_store_data()