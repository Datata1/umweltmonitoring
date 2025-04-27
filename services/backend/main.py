import os

from fastapi import FastAPI
import logging
import asyncio
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import timedelta
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from utils.db_session import SessionLocal
from core.config import settings
from shared.crud import crud_sensor


# Router
from api.v1.endpoints import sensors as sensors_router

# Importiere FastAPICache und Redis Backend
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from prefect.deployments import run_deployment
from prefect.exceptions import ObjectNotFound

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR)))
print(project_root)
STATIC_DIR = os.path.join(project_root, "app", "assets")
FAVICON_PATH = os.path.join(STATIC_DIR, "favicon.ico")


# Initialisiere den Scheduler
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Startup: Initializing database...")
    try:
        # 2. Initiale Datenbeschaffung 
        logger.info("Startup: Performing initial data ingestion...")
        db = SessionLocal()
        sensor_box = crud_sensor.sensor_box.get(db, id=settings.SENSOR_BOX_ID)
        if sensor_box:
            box_exists_in_db = True
            logger.info(f"SensorBox '{settings.SENSOR_BOX_ID}' existiert bereits in der Datenbank.")
        else:
            box_exists_in_db = False
            logger.info(f"SensorBox '{settings.SENSOR_BOX_ID}' wurde nicht in der Datenbank gefunden.")
        db.close()

        if not box_exists_in_db:
            flow_name = "data-ingestion-flow"  
            deployment_name_only = "timeseries-data-ingestion"
            full_deployment_identifier = f"{flow_name}/{deployment_name_only}"
            logger.warning(f"SensorBox '{settings.SENSOR_BOX_ID}' nicht gefunden. Starte initialen Prefect Flow Run über Deployment '{full_deployment_identifier}'...")

            # --- Retry Logic ---
            max_attempts = 10
            delay_seconds = 3
            run_submitted_successfully = False

            flow_run_params = {
                "box_id": settings.SENSOR_BOX_ID,
                "initial_fetch_days": settings.INITIAL_TIME_WINDOW_IN_DAYS,
                "fetch_chunk_days": settings.FETCH_TIME_WINDOW_DAYS
            }

            for attempt in range(max_attempts):
                logger.info(f"Versuch {attempt + 1}/{max_attempts} zum Starten des Deployments '{full_deployment_identifier}'...")
                try:
                    flow_run = await run_deployment(
                        name=full_deployment_identifier,
                        parameters=flow_run_params,
                        timeout=10
                    )
                    logger.info(f"Prefect Flow Run erfolgreich gestartet: Name='{flow_run.name}', ID='{flow_run.id}'")
                    run_submitted_successfully = True
                    break 

                except ObjectNotFound:
                    logger.error(f"Versuch {attempt + 1}: Prefect Deployment '{full_deployment_identifier}' konnte nicht gefunden werden.")
                    if attempt < max_attempts - 1:
                        logger.info(f"Warte {delay_seconds} Sekunde(n) vor dem nächsten Versuch...")
                        await asyncio.sleep(delay_seconds) 
                except Exception as e:
                    logger.error(f"Versuch {attempt + 1}: Fehler beim Starten des Prefect Flow Runs: {e}", exc_info=False) 
                    if attempt < max_attempts - 1:
                        logger.info(f"Warte {delay_seconds} Sekunde(n) vor dem nächsten Versuch...")
                        await asyncio.sleep(delay_seconds) 
                    else:
                        logger.error(f"Initialen Flow Run konnte nach {max_attempts} Versuchen nicht gestartet werden.")


        logger.info("Startup: Initial data ingestion complete.")

        # 3. FastAPICache initialisieren
        logger.info(f"Startup: Initializing Redis connection to {settings.REDIS_HOST}:{settings.REDIS_PORT}...")
        redis_conn = aioredis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}", encoding="utf8", decode_responses=False)
        FastAPICache.init(RedisBackend(redis_conn), prefix="fastapi-cache")
        logger.info("Startup: Redis connection and FastAPICache initialized.")

    except Exception as e:
        logger.error(f"CRITICAL: Application startup failed: {e}")
        # Stelle sicher, dass der Scheduler im Fehlerfall heruntergefahren wird
        if scheduler.running:
            scheduler.shutdown()
        raise RuntimeError(f"Application startup failed: {e}") from e

    yield # Die Anwendung läuft hier

    logger.info("Shutdown: Cleaning up...")
    # 4. Scheduler beim Herunterfahren anhalten
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Shutdown: Scheduler stopped.")
    logger.info("Shutdown complete.")

    # Falls nötig hier weitere Aufräumarbeiten hinzufügen

app = FastAPI(
    title="Umweltmonitoring Backend",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(FAVICON_PATH)

app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


app.include_router(sensors_router.router, prefix="/api/v1", tags=["sensors"])