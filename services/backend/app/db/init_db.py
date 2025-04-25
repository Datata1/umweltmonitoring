# services/backend/app/db/init_db.py
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, OperationalError
from sqlalchemy.engine import Engine
from tenacity import retry, stop_after_delay, wait_fixed, retry_if_exception_type

from app.core.config import settings
from app.db.session import engine as main_app_engine # Engine, die mit DB_NAME verbunden ist
from app.models.base import Base
from app.models.sensor import SensorBox, SensorData # Füge dies hinzu

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_TRIES = 60 * 5  
WAIT_SECONDS = 1

@retry(
    stop=stop_after_delay(MAX_TRIES * WAIT_SECONDS),
    wait=wait_fixed(WAIT_SECONDS),
    retry=retry_if_exception_type(OperationalError), 
    before_sleep=lambda retry_state: logger.info(f"Retrying DB connection... ({retry_state.attempt_number})")
)
def check_db_connection(engine_to_check: Engine):
    """Prüft, ob eine Verbindung mit der gegebenen Engine möglich ist."""
    try:
        connection = engine_to_check.connect()
        connection.close()
        logger.info(f"Connection check successful for engine: {engine_to_check.url.database}")
    except OperationalError as e:
        logger.error(f"Connection check failed for engine {engine_to_check.url.database}: {e}")
        raise 


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
                connection.execute(text(f'CREATE DATABASE "{settings.DB_NAME}"'))
                logger.info(f"Database '{settings.DB_NAME}' created successfully.")
                connection.execute(text(f'CREATE DATABASE "{settings.PREFECT_DB_NAME}"'))
                logger.info(f"Database '{settings.PREFECT_DB_NAME}' created successfully.")
            else:
                logger.info(f"Database '{settings.DB_NAME}' already exists.")
    except Exception as e:
        logger.error(f"Error during database check/creation: {e}")
        raise
    finally:
        maint_engine.dispose()


def relation_exists(connection, relation_name):
    query = text("""
        SELECT EXISTS (
            SELECT 1
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' 
            AND c.relname = :relation_name
        );
    """)
    return connection.execute(query, {"relation_name": relation_name}).scalar()


def create_extensions_and_tables():
    """Stellt Verbindung zur Haupt-DB her, erstellt Extensions, Tabellen und kontinuierliche Aggregate."""
    logger.info(f"Ensuring extensions, tables, and continuous aggregates exist in database '{settings.DB_NAME}'...")

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
            logger.info("Application tables checked/created.")

            # 3. SensorData Tabelle in eine Hypertable umwandeln (nur wenn nicht bereits eine ist)
            hypertable_name = 'sensor_data'
            logger.info(f"Checking if {hypertable_name} is already a TimescaleDB hypertable...")
            is_hypertable_result = connection.execute(
                text(
                    "SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_name = :hypertable_name;"
                ), {"hypertable_name": hypertable_name}
            ).scalar()

            if not is_hypertable_result:
                logger.info(f"Converting {hypertable_name} table to a TimescaleDB hypertable...")
                try:
                    connection.execute(
                        text(f"SELECT create_hypertable('{hypertable_name}', by_range('measurement_timestamp'));")
                    )
                    connection.execute(
                        text(f"SELECT add_dimension('{hypertable_name}', by_hash('sensor_id', 8));")
                    )
                    connection.commit()
                    logger.info(f"{hypertable_name} table successfully converted to a hypertable with time and space partitioning.")
                except ProgrammingError as e:
                    logger.warning(f"Could not create hypertable {hypertable_name} (might already exist or other error): {e}")

            else:
                logger.info(f"{hypertable_name} table is already a TimescaleDB hypertable.")

    except Exception as e:
        logger.error(f"Error creating extensions or tables in '{settings.DB_NAME}': {e}", exc_info=True) 
        raise


def initialize_database():
    """Orchestriert die gesamte Datenbank-Initialisierung."""
    logger.info("Starting database initialization...")

    # Schritt 1: Hauptdatenbank erstellen (falls nötig)
    create_database_if_not_exists()

    # Schritt 2: Extensions, Tabellen und kontinuierliche Aggregate in der Hauptdatenbank erstellen
    create_extensions_and_tables()

    logger.info("Database initialization finished successfully.")