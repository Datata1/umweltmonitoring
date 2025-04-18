from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import sensor as sensor_model
from app.schemas import sensor as sensor_schema

class CRUDSensorBox:
    def get(self, db: Session, id: str) -> Optional[sensor_model.SensorBox]:
        return db.query(sensor_model.SensorBox).filter(sensor_model.SensorBox.box_id == id).first()

    def create(self, db: Session, *, obj_in: sensor_schema.SensorBoxCreate) -> sensor_model.SensorBox:
        db_obj = sensor_model.SensorBox(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: sensor_model.SensorBox, obj_in: sensor_schema.SensorBoxUpdate) -> sensor_model.SensorBox:
        update_data = obj_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_obj, key, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


class CRUDSensor:
    def get(self, db: Session, id: str) -> Optional[sensor_model.Sensor]:
        return db.query(sensor_model.Sensor).filter(sensor_model.Sensor.sensor_id == id).first()

    def create(self, db: Session, *, obj_in: sensor_schema.SensorCreate) -> sensor_model.Sensor:
        db_obj = sensor_model.Sensor(
            sensor_id=obj_in.sensor_id,
            box_id=obj_in.box_id,
            title=obj_in.title,
            sensor_type=obj_in.sensor_type,
            unit=obj_in.unit,
            icon=obj_in.icon
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: sensor_model.Sensor, obj_in: sensor_schema.SensorUpdate) -> sensor_model.Sensor:
        update_data = obj_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_obj, key, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


class CRUDSensorData:
    def create_multi(self, db: Session, *, objs_in: List[sensor_schema.SensorDataCreate]) -> List[sensor_model.SensorData]:
        db_objs = (sensor_model.SensorData(**obj_in.model_dump()) for obj_in in objs_in)
        db.bulk_save_objects(db_objs)
        db.commit()
        return list(db_objs)


sensor_box = CRUDSensorBox()
sensor = CRUDSensor()
sensor_data = CRUDSensorData()