from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

# --- SensorBox Schemas ---

class SensorBoxBase(BaseModel):
    name: str
    exposure: Optional[str] = None
    model: Optional[str] = None
    currentLocation: Optional[dict] = None
    lastMeasurementAt: Optional[datetime] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

class SensorBoxCreate(SensorBoxBase):
    box_id: str

class SensorBoxUpdate(SensorBoxBase):
    model_config = ConfigDict(from_attributes=True)
    name: Optional[str] = None
    box_id: Optional[str] = None

class SensorBox(SensorBoxBase):
    box_id: str

    class Config:
        orm_mode = True

# --- Sensor Schemas ---

class SensorBase(BaseModel):
    box_id: str
    sensor_id_from_api: Optional[str] = None
    title: Optional[str] = None
    sensor_type: str
    unit: str
    icon: Optional[str] = None

class SensorCreate(SensorBase):
    sensor_id: str

class SensorUpdate(SensorBase):
    box_id: Optional[str] = None
    sensor_id_from_api: Optional[str] = None
    title: Optional[str] = None
    sensor_type: Optional[str] = None
    unit: Optional[str] = None
    icon: Optional[str] = None
    sensor_id: Optional[str] = None

class Sensor(SensorBase):
    sensor_id: str

    class Config:
        orm_mode = True

# --- SensorData Schemas ---

class SensorDataBase(BaseModel):
    sensor_id: str
    value: float
    measurement_timestamp: datetime

class SensorDataCreate(SensorDataBase):
    pass

class SensorData(SensorDataBase):
    id: int

    class Config:
        orm_mode = True