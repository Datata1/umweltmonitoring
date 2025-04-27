# services/backend/app/api/v1/endpoints/sensors.py
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session
from datetime import datetime

from utils.db_session import get_db
from shared.crud import crud_sensor
from shared.schemas import sensor as sensor_schema
from utils.keybuilder import (
    aggregate_key_builder,
    list_sensors_key_builder,
    raw_data_key_builder,
    box_detail_key_builder,      
    sensors_for_box_key_builder, 
    summary_stats_key_builder    
)

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- GET Endpunkte (für das Frontend) ---

@router.get("/sensor_boxes", response_model=List[sensor_schema.SensorBox])
@cache(expire=900, key_builder=list_sensors_key_builder) 
def read_sensor_boxes(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Ruft eine Liste aller Sensorboxen ab.
    """
    logger.info(f"--> Cache MISS! Führe DB-Abfrage aus...")
    sensor_boxes = crud_sensor.sensor_box.get_multi(db, skip=skip, limit=limit)
    return sensor_boxes 

@router.get("/sensor_boxes/{box_id}", response_model=sensor_schema.SensorBox)
@cache(expire=900, key_builder=box_detail_key_builder) 
def read_sensor_box(
    box_id: str,
    db: Session = Depends(get_db)
):
    """
    Ruft Details einer spezifischen Sensorbox ab.
    """
    logger.info(f"--> Cache MISS! Führe DB-Abfrage aus...")
    db_sensor_box = crud_sensor.sensor_box.get(db, id=box_id)
    if db_sensor_box is None:
        raise HTTPException(status_code=404, detail="SensorBox not found")
    return db_sensor_box 

@router.get("/sensor_boxes/{box_id}/sensors", response_model=List[sensor_schema.Sensor]) 
@cache(expire=900, key_builder=sensors_for_box_key_builder) 
def read_sensors_for_box(
    box_id: str,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Ruft alle Sensoren für eine spezifische Sensorbox ab.
    """
    logger.info(f"--> Cache MISS! Führe DB-Abfrage aus...")
    db_sensor_box = crud_sensor.sensor_box.get(db, id=box_id)
    if db_sensor_box is None:
        raise HTTPException(status_code=404, detail="SensorBox not found")

    sensors = crud_sensor.sensor.get_multi_by_box_id(db, box_id=box_id, skip=skip, limit=limit)
    return sensors 

@router.get("/sensors/{sensor_id}/data", response_model=List[sensor_schema.SensorData]) 
@cache(expire=900, key_builder=raw_data_key_builder) 
def read_sensor_data(
    sensor_id: str,
    db: Session = Depends(get_db),
    from_date: Optional[datetime] = Query(None, description="Start date for measurements (RFC3339 format, e.g., 2023-01-01T10:00:00Z)"),
    to_date: Optional[datetime] = Query(None, description="End date for measurements (RFC3339 format, e.g., 2023-01-01T12:00:00Z)"),
    skip: int = 0,
    limit=1000
):
    """
    Ruft Datenpunkte für einen spezifischen Sensor ab, optional innerhalb eines Zeitraums.
    """
    logger.info(f"--> Cache MISS! Führe DB-Abfrage aus...")
    db_sensor = crud_sensor.sensor.get(db, id=sensor_id)
    if db_sensor is None:
        raise HTTPException(status_code=404, detail="Sensor not found")

    data_points = crud_sensor.sensor_data.get_by_sensor_id(
        db,
        sensor_id=sensor_id,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return data_points


@router.get("/sensors/{sensor_id}/data/daily_summary", response_model=sensor_schema.SensorDataDailySummaries)
@cache(expire=900, key_builder=summary_stats_key_builder) 
def read_sensor_data_daily_summary(
    sensor_id: str,
    from_date: datetime = Query(..., alias="from-date", description="Start date for aggregation (RFC3339 format)"), # Füge alias="from-date" hinzu
    to_date: datetime = Query(..., alias="to-date", description="End date for aggregation (RFC3339 format)"),     # Füge alias="to-date" hinzu
    db: Session = Depends(get_db)
):
    """
    Ruft tägliche Zusammenfassungen (Min, Max, Avg, Count) für einen spezifischen Sensor in einem Zeitraum ab.
    """
    logger.info(f"--> Cache MISS! Führe DB-Abfrage aus...")
    db_sensor = crud_sensor.sensor.get(db, id=sensor_id)
    if db_sensor is None:
        raise HTTPException(status_code=404, detail="Sensor not found")

    daily_summaries = crud_sensor.sensor_data.get_daily_summary_by_sensor_id(
        db,
        sensor_id=sensor_id,
        from_date=from_date,
        to_date=to_date
    )
    return {"unit": db_sensor.unit, "daily_summaries": daily_summaries}


@router.get("/sensors/{sensor_id}/stats/", response_model=sensor_schema.SensorDataStatistics)
@cache(expire=900, key_builder=summary_stats_key_builder) 
def read_sensor_data_statistics(
    sensor_id: str,
    from_date: datetime = Query(..., alias="from-date", description="Start date for statistics (RFC3339 format)"),
    to_date: datetime = Query(..., alias="to-date", description="End date for statistics (RFC3339 format)"),
    db: Session = Depends(get_db)
):
    """
    Ruft statistische Kennzahlen (Avg, Min, Max, Count, StdDev) für einen spezifischen Sensor in einem Zeitraum ab.
    """
    logger.info(f"--> Cache MISS! Führe DB-Abfrage aus...")
    db_sensor = crud_sensor.sensor.get(db, id=sensor_id)
    if db_sensor is None:
        raise HTTPException(status_code=404, detail="Sensor not found")

    statistics = crud_sensor.sensor_data.get_statistics_by_sensor_id(
        db,
        sensor_id=sensor_id,
        from_date=from_date,
        to_date=to_date
    )

    return statistics


@router.get("/sensors/{sensor_id}/data/aggregate/", response_model=sensor_schema.SensorDataAggregatedResponse)
@cache(expire=900, key_builder=aggregate_key_builder) 
def read_sensor_data_aggregate(
    sensor_id: str,
    from_date: datetime = Query(..., alias="from-date", description="Start date for aggregation (RFC3339 format)"),
    to_date: datetime = Query(..., alias="to-date", description="End date for aggregation (RFC3339 format)"),
    interval: str = Query(..., description="Aggregation interval (e.g., '5m', '15m', '1h', '1d', '1w', '1M')"),
    aggregation_type: str = Query(..., description="Type of aggregation ('avg', 'min', 'max', 'count', 'sum')"),
    smoothing_window: Optional[int] = Query(None, gt=0, description="Optional: Window size for smoothing on aggregated data"),
    interpolation_method: Optional[str] = Query(None, description="Optional: Method for gap filling ('linear', 'locf')"),
    db: Session = Depends(get_db)
):
    """
    Ruft aggregierte Daten für einen spezifischen Sensor in einem Zeitraum mit flexiblem Intervall und Aggregationstyp ab,
    nutzt optional kontinuierliche Aggregate, wendet optional Glättung/Interpolation an und inkludiert die Einheit.
    """
    logger.info(f"Request received for sensor {sensor_id} with interval={interval}, agg_type={aggregation_type}, smoothing={smoothing_window}, interpolation={interpolation_method}")
    logger.info(f"--> Cache MISS! Führe DB-Abfrage aus...")

    db_sensor = crud_sensor.sensor.get(db, id=sensor_id)
    if db_sensor is None:
        raise HTTPException(status_code=404, detail="Sensor not found")

    use_continuous_aggregate = False
    aggregated_data = []

    # Wenn keine passende kontinuierliche Aggregation verwendet wurde oder Fehler auftraten
    if not use_continuous_aggregate:
        logger.info(f"Falling back to raw data aggregation for sensor {sensor_id}")
        try:
            aggregated_data = crud_sensor.sensor_data.get_aggregated_data_by_sensor_id( 
                db,
                sensor_id=sensor_id,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                aggregation_type=aggregation_type,
                smoothing_window=smoothing_window,
                interpolation_method=interpolation_method
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {
        "unit": db_sensor.unit,
        "aggregation_type": aggregation_type,
        "interval": interval,
        "aggregated_data": aggregated_data 
    }
