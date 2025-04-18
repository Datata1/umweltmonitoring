import os

from fastapi import FastAPI
import logging
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import timedelta
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.db.init_db import initialize_database
from app.db.data_ingestion import fetch_and_store_data

# Router
from app.api.v1.endpoints import sensors as sensors_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR)))
STATIC_DIR = os.path.join(project_root, "assets")
FAVICON_PATH = os.path.join(STATIC_DIR, "favicon.ico")


# Initialisiere den Scheduler
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Startup: Initializing database...")
    try:
        # 1. Datenbankinitialisierung
        await run_in_threadpool(initialize_database)
        logger.info("Startup: Database initialization complete.")

        # 2. Initiale Datenbeschaffung
        logger.info("Startup: Performing initial data ingestion...")
        await run_in_threadpool(fetch_and_store_data)
        logger.info("Startup: Initial data ingestion complete.")

        # 3. Periodische Datenbeschaffung planen
        logger.info("Startup: Scheduling periodic data ingestion...")
        scheduler.add_job(
            run_in_threadpool, 
            trigger=IntervalTrigger(minutes=1), 
            args=[fetch_and_store_data], 
            id='periodic_data_ingestion',
            replace_existing=True
        )
        scheduler.start()
        logger.info("Startup: Periodic data ingestion scheduled.")

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