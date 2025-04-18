from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

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
    model_config = ConfigDict(from_attributes=True) 
    box_id: str


# --- Sensor Schemas ---
class SensorBase(BaseModel):
    box_id: str
    sensor_id: Optional[str] = None
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
    model_config = ConfigDict(from_attributes=True) 

# --- SensorData Schemas ---

class SensorDataBase(BaseModel):
    sensor_id: str
    value: float
    measurement_timestamp: datetime

class SensorDataCreate(SensorDataBase):
    pass

class SensorData(SensorDataBase):
    model_config = ConfigDict(from_attributes=True) # Füge diese Zeile hinzu
    id: int


# Schemas für Listen von Objekten
class SensorBoxes(BaseModel):
    sensor_boxes: List[SensorBox]

class Sensors(BaseModel):
    sensors: List[Sensor]

class SensorDataPoints(BaseModel):
    data_points: List[SensorData]


class SensorDataHourlyAverage(BaseModel):
    """ Schema für stündliche Durchschnittswerte """
    hour: datetime # <-- Geänderter Feldname
    average_value: float # <-- Feldname bleibt gleich

    model_config = ConfigDict(from_attributes=True)


class SensorDataDailySummary(BaseModel):
    """ Schema für tägliche Zusammenfassungen (Min, Max, Avg, Count) """
    timestamp: datetime = Field(..., alias="day") # Nutze alias, um das Feld 'day' aus der Query auf 'timestamp' zu mappen
    min_value: float
    max_value: float
    average_value: float
    count: int # Anzahl der Datenpunkte im Intervall

    model_config = ConfigDict(from_attributes=True)


class SensorDataHourlyAverages(BaseModel):
    unit: str
    average_value: List[SensorDataHourlyAverage]

class SensorDataDailySummaries(BaseModel):
    unit: str
    daily_summaries: List[SensorDataDailySummary]

    
class SensorDataStatistics(BaseModel):
    """ Schema für statistische Kennzahlen eines Sensors in einem Zeitraum """
    average_value: Optional[float] = None # Optional, falls keine Daten im Zeitraum
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    count: int # Anzahl der Datenpunkte (kann 0 sein)
    stddev_value: Optional[float] = None # Standardabweichung (TimescaleDB/PostgreSQL hat stddev)

    model_config = ConfigDict(from_attributes=True)

class SensorDataAggregatedPoint(BaseModel):
    """ Schema für einen generischen aggregierten Datenpunkt """
    timestamp: datetime = Field(..., alias="time_bucket") # Nutze alias, um den Spaltennamen 'time_bucket' aus der Query auf 'timestamp' zu mappen
    aggregated_value: Optional[float] = None # Der aggregierte Wert (kann Avg, Min, Max, Sum sein)
    count: Optional[int] = None # Nur relevant für 'count' oder Aggregationen, die Anzahl einschließen (z.B. daily summary)

    model_config = ConfigDict(from_attributes=True)


class SensorDataAggregatedResponse(BaseModel):
    """ Antwortschema für flexible Aggregation mit Einheit """
    unit: str
    aggregation_type: str # Welcher Aggregationstyp wurde verwendet (z.B. 'avg', 'min')
    interval: str # Welches Zeitintervall wurde verwendet (z.B. '1h', '1d')
    aggregated_data: List[SensorDataAggregatedPoint]
