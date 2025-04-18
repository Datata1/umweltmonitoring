# services/backend/app/db/init_db.py
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, OperationalError
from sqlalchemy.engine import Engine
from tenacity import retry, stop_after_delay, wait_fixed, retry_if_exception_type

from app.core.config import settings
from app.db.session import engine as main_app_engine # Engine, die mit DB_NAME verbunden ist
from app.models.base import Base
from app.models.sensor import SensorBox, SensorData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_TRIES = 60 * 5  # 5 Minuten
WAIT_SECONDS = 1

@retry(
    stop=stop_after_delay(MAX_TRIES * WAIT_SECONDS),
    wait=wait_fixed(WAIT_SECONDS),
    retry=retry_if_exception_type(OperationalError), # Nur bei Verbindungsfehlern wiederholen
    before_sleep=lambda retry_state: logger.info(f"Retrying DB connection... ({retry_state.attempt_number})")
)
def check_db_connection(engine_to_check: Engine):
    """Prüft, ob eine Verbindung mit der gegebenen Engine möglich ist."""
    try:
        # Versuche, eine Verbindung herzustellen und wieder zu schließen
        connection = engine_to_check.connect()
        connection.close()
        logger.info(f"Connection check successful for engine: {engine_to_check.url.database}")
    except OperationalError as e:
        logger.error(f"Connection check failed for engine {engine_to_check.url.database}: {e}")
        raise # Erneut auslösen, damit tenacity es fängt und wiederholt


def create_database_if_not_exists():
    """Stellt Verbindung zur 'postgres'-DB her und erstellt die Haupt-DB falls nötig."""
    logger.info(f"Checking if database '{settings.DB_NAME}' exists...")
    if not settings.MAINTENANCE_DATABASE_URL:
         logger.error("MAINTENANCE_DATABASE_URL is not set in settings.")
         raise ValueError("MAINTENANCE_DATABASE_URL is required.")

    maint_engine = create_engine(settings.MAINTENANCE_DATABASE_URL, isolation_level="AUTOCOMMIT")

    try:
        check_db_connection(maint_engine)

        with maint_engine.connect() as connection:
            check_db_query = text("SELECT 1 FROM pg_database WHERE datname = :db_name")
            result = connection.execute(check_db_query, {"db_name": settings.DB_NAME}).scalar()

            if not result:
                logger.info(f"Database '{settings.DB_NAME}' does not exist. Creating...")
                # WICHTIG: Sicherstellen, dass der DB_NAME keine SQL-Injection ermöglicht.
                connection.execute(text(f'CREATE DATABASE "{settings.DB_NAME}"'))
                logger.info(f"Database '{settings.DB_NAME}' created successfully.")
            else:
                logger.info(f"Database '{settings.DB_NAME}' already exists.")
    except Exception as e:
        logger.error(f"Error during database check/creation: {e}")
        raise
    finally:
        maint_engine.dispose() 


def create_extensions_and_tables():
    """Stellt Verbindung zur Haupt-DB her, erstellt Extensions und Tabellen."""
    logger.info(f"Ensuring extensions and tables exist in database '{settings.DB_NAME}'...")

    check_db_connection(main_app_engine)

    try:
        with main_app_engine.connect() as connection:
            # 1. TimescaleDB Extension erstellen (falls nötig)
            logger.info("Creating TimescaleDB extension if not exists...")
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
            connection.commit() 
            logger.info("TimescaleDB extension checked/created.")

            # 2. Tabellen erstellen
            logger.info("Creating application tables if not exists...")
            Base.metadata.create_all(bind=main_app_engine) 
            SensorBox.metadata.create_all(bind=main_app_engine) 
            SensorData.metadata.create_all(bind=main_app_engine) 
            logger.info("Application tables checked/created.")

            # 3. SensorData Tabelle in eine Hypertable umwandeln (nur wenn nicht bereits eine ist)
            logger.info("Checking if sensor_data is already a TimescaleDB hypertable...")
            is_hypertable_result = connection.execute(
                text(
                    "SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_name = 'sensor_data';"
                )
            ).scalar()

            if not is_hypertable_result:
                logger.info("Converting sensor_data table to a TimescaleDB hypertable...")
                connection.execute(
                    text("SELECT create_hypertable('sensor_data', by_range('measurement_timestamp'));")
                )
                connection.commit()
                logger.info("sensor_data table successfully converted to a hypertable with time partitioning.")

                # 4. Zusätzliche Partitionierungsdimension für sensor_id hinzufügen (nur wenn die Hypertable gerade erstellt wurde)
                logger.info("Adding partitioning dimension for sensor_id...")
                try:
                    connection.execute(
                        text("SELECT add_dimension('sensor_data', by_hash('sensor_id', 8));")
                    )
                    connection.commit()
                    logger.info("Partitioning dimension for sensor_id added.")
                except ProgrammingError as e:
                    logger.warning(f"Could not add dimension (might already exist or other error): {e}")
            else:
                logger.info("sensor_data table is already a TimescaleDB hypertable.")

    except Exception as e:
        logger.error(f"Error creating extensions or tables in '{settings.DB_NAME}': {e}")
        raise



def initialize_database():
    """Orchestriert die gesamte Datenbank-Initialisierung."""
    logger.info("Starting database initialization...")

    # Schritt 1: Hauptdatenbank erstellen (falls nötig)
    create_database_if_not_exists()

    # Schritt 2: Extensions und Tabellen in der Hauptdatenbank erstellen
    create_extensions_and_tables()

    logger.info("Database initialization finished successfully.")