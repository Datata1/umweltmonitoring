# utils/db_utils.py

import os
from typing import Iterator
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from prefect import get_run_logger

from .config import settings

DATABASE_URL = settings.DATABASE_URL

engine = None
SessionLocal = None

if not DATABASE_URL:
    print("Umgebungsvariable 'DATABASE_URL_PREFECT' ist nicht gesetzt! Datenbankverbindung nicht möglich.")
else:
    try:
        # Erstelle die Engine einmal beim Laden des Moduls.
        # Die Engine verwaltet den Connection Pool.
        # Passe pool_size etc. an deine erwartete Parallelität an.
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,  # Prüft Verbindungen vor der Nutzung
            echo=False,          # SQL-Logging aus (in Tasks meist unerwünscht)
            pool_size=5,         # Beispiel: Max 5 Verbindungen im Pool
            max_overflow=10      # Beispiel: Erlaube 10 zusätzliche Verbindungen unter Last
        )

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        with engine.connect() as connection:
             print("Datenbank-Engine erfolgreich erstellt und Verbindung getestet.")

    except Exception as e:
        print(f"Fehler beim Erstellen der SQLAlchemy Engine: {e}", exc_info=True)
        engine = None
        SessionLocal = None

@contextmanager
def get_db_session() -> Iterator[Session | None]:
    """
    Stellt eine SQLAlchemy Session für die Nutzung in einem Task bereit.
    Handhabt Commit, Rollback und Schließen der Session.

    Verwendung:
        with get_db_session() as db:
            if db:
                # ... deine Datenbankoperationen mit 'db' ...
            else:
                # Fehlerbehandlung, wenn keine Session erstellt werden konnte
    """
    task_logger = get_run_logger() 
    if SessionLocal is None:
        task_logger.error("SessionLocal ist nicht initialisiert. Engine-Erstellung fehlgeschlagen?")
        yield None # Wichtig: yield None, damit der 'with'-Block es prüfen kann
        return

    session = SessionLocal()
    task_logger.debug(f"Datenbank-Session {id(session)} erstellt.")
    try:
        yield session
        session.commit()
        task_logger.debug(f"Datenbank-Session {id(session)} committed.")
    except Exception as e:
        task_logger.error(f"Fehler in Datenbank-Session {id(session)}: {e}. Führe Rollback aus.", exc_info=True)
        session.rollback()
        raise 
    finally:
        task_logger.debug(f"Datenbank-Session {id(session)} wird geschlossen.")
        session.close()

def get_engine_instance():
    if engine is None:
        raise RuntimeError("Datenbank Engine wurde nicht erfolgreich initialisiert.")
    return engine