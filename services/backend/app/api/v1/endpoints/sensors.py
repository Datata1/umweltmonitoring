from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.crud import crud_sensor
from app.schemas import sensor as sensor_schema

router = APIRouter()


# Sensorboxen
@router.post("/sensor_boxes/", response_model=sensor_schema.SensorBox)
def create_sensor_box(sensor_box_in: sensor_schema.SensorBoxCreate, db: Session = Depends(get_db)):
    """
    Erstellt eine neue Sensorbox.
    """
    return crud_sensor.sensor_box.create(db=db, obj_in=sensor_box_in)

@router.put("/sensor_boxes/{box_id}", response_model=sensor_schema.SensorBox)
def update_sensor_box(box_id: str, sensor_box_in: sensor_schema.SensorBoxUpdate, db: Session = Depends(get_db)):
    """
    Aktualisiert eine bestehende Sensorbox.
    """
    db_sensor_box = crud_sensor.sensor_box.get(db=db, id=box_id)
    if not db_sensor_box:
        return None
    return crud_sensor.sensor_box.update(db=db, db_obj=db_sensor_box, obj_in=sensor_box_in)


# Sensoren
@router.post("/sensors/", response_model=sensor_schema.Sensor)
def create_sensor(sensor_in: sensor_schema.SensorCreate, db: Session = Depends(get_db)):
    """
    Erstellt einen neuen Sensor.
    """
    return crud_sensor.sensor.create(db=db, obj_in=sensor_in)

@router.put("/sensors/{sensor_id}", response_model=sensor_schema.Sensor)
def update_sensor(sensor_id: str, sensor_in: sensor_schema.SensorUpdate, db: Session = Depends(get_db)):
    """
    Aktualisiert einen bestehenden Sensor.
    """
    db_sensor = crud_sensor.sensor.get(db=db, id=sensor_id)
    if not db_sensor:
        return None
    return crud_sensor.sensor.update(db=db, db_obj=db_sensor, obj_in=sensor_in)


# sensor_data
@router.post("/sensor_data/bulk/", response_model=List[sensor_schema.SensorData])
def create_sensor_data_bulk(sensor_data_in: List[sensor_schema.SensorDataCreate], db: Session = Depends(get_db)):
    """
    Erstellt mehrere Sensor-Datenpunkte.
    """
    return crud_sensor.sensor_data.create_multi(db=db, objs_in=sensor_data_in)