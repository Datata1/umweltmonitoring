# utils/fetch_window.py

from prefect import task, get_run_logger
from typing import Dict, Any, Tuple
from datetime import datetime, timezone

from utils.parse_datetime import parse_api_datetime

@task(name="Determine Fetch Time Window", log_prints=True)
def determine_fetch_window(
    db_box_state: Dict[str, Any],
    api_last_measurement_str: str | None
) -> Tuple[datetime | None, datetime | None]:
    """
    Bestimmt das Zeitfenster (von, bis) für den Abruf von Sensordaten,
    basierend auf dem letzten Abruf und der letzten Messung laut API.
    """
    logger = get_run_logger()
    box_id = db_box_state.get("box_id", "UNKNOWN") 

    # --- 1. End-Datum bestimmen (to_date) ---
    now_utc = datetime.now(timezone.utc)
    api_last_measurement_dt = parse_api_datetime(api_last_measurement_str)
    logger.info(f"[Fetch Window {box_id}] API Last Measurement: {api_last_measurement_dt}")

    target_to_date = api_last_measurement_dt if api_last_measurement_dt else now_utc
    actual_to_date = min(target_to_date, now_utc)

    actual_to_date = actual_to_date.astimezone(timezone.utc)
    logger.info(f"[Fetch Window {box_id}] Ziel-Enddatum (To Date): {actual_to_date}")

    # --- 2. Start-Datum bestimmen (from_date) ---
    db_last_data_fetched = db_box_state.get("db_last_data_fetched")

    actual_from_date = None
    if db_last_data_fetched:
        if isinstance(db_last_data_fetched, datetime):
            actual_from_date = db_last_data_fetched.astimezone(timezone.utc)
        else:
            logger.warning(f"[Fetch Window {box_id}] Unerwarteter Typ '{type(db_last_data_fetched)}' für 'db_last_data_fetched'. Versuche Parsing.")
            actual_from_date = parse_api_datetime(str(db_last_data_fetched))

    logger.info(f"[Fetch Window {box_id}] Letzter erfolgreicher Abruf bis (From Date): {actual_from_date}")

    # --- 3. Prüfen, ob Abruf nötig ist ---
    if actual_from_date and actual_from_date >= actual_to_date:
        logger.info(f"[Fetch Window {box_id}] Daten sind aktuell (From >= To). Kein Abruf nötig.")
        return None, None 

    logger.info(f"[Fetch Window {box_id}] Abruf nötig. Fenster: VON '{actual_from_date}' BIS '{actual_to_date}'")
    return actual_from_date, actual_to_date