from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, PrimaryKeyConstraint, Table, MetaData
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone

from .base import Base 


class SensorBox(Base):
    __tablename__ = "sensor_box"

    box_id: Mapped[str] = mapped_column(String(50), primary_key=True) # ID der Sensorbox aus der API
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    exposure: Mapped[str | None] = mapped_column(String(50))
    model: Mapped[str | None] = mapped_column(String(100))
    currentLocation: Mapped[dict | None] = mapped_column(JSON) # Oder separate Spalten oder geo extension hinzufügen um geo Daten zu speichern
    lastMeasurementAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_data_fetched: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Beziehung zu Sensor (eine Box hat mehrere Sensoren)
    sensors: Mapped[list["Sensor"]] = relationship("Sensor", back_populates="box")


class Sensor(Base):
    __tablename__ = "sensor"

    sensor_id: Mapped[str] = mapped_column(String(50), primary_key=True) # ID des Sensors aus der API
    box_id: Mapped[str] = mapped_column(ForeignKey("sensor_box.box_id")) # ID der Sensorbox aus der API
    title: Mapped[str | None] = mapped_column(String(100)) # Der Titel des Sensors
    sensor_type: Mapped[str] = mapped_column(String(50)) # Der technische Typ des Sensors
    unit: Mapped[str] = mapped_column(String(20)) # Z.B. "µg/m³", "°C", "%", "Pa"
    icon: Mapped[str | None] = mapped_column(String(50)) # Das Icon des Sensors

    # Beziehung zu SensorBox
    box: Mapped["SensorBox"] = relationship("SensorBox", back_populates="sensors")

    # Beziehung zu SensorData (ein Sensor hat viele Messpunkte)
    data: Mapped[list["SensorData"]] = relationship("SensorData", back_populates="sensor")


class SensorData(Base):
    __tablename__ = "sensor_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True) # Behalten wir als internen Zähler für die Messdaten
    sensor_id: Mapped[str] = mapped_column(ForeignKey("sensor.sensor_id")) # ID des Sensors aus der API
    value: Mapped[float] = mapped_column(Float)
    measurement_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, index=True) # Zeitpunkt der Messung vom Sensor

    # Beziehung zurück zu Sensor
    sensor: Mapped["Sensor"] = relationship("Sensor", back_populates="data")

    __table_args__ = (
        PrimaryKeyConstraint('id', 'measurement_timestamp', 'sensor_id'),
    )


sensor_data_hourly_avg_view = Table(
    "sensor_data_hourly_avg", # Der Name der Materialized View in der Datenbank
    Base.metadata, # Oder verwende eine separate MetaData() Instanz, falls bevorzugt
    Column("hour", DateTime(timezone=True)), # Der Zeitstempel-Spaltenname in der View
    Column("sensor_id", String(50)),      # Der sensor_id Spaltenname in der View
    Column("average_value", Float),      # Der aggregierte Wert Spaltenname in der View
)

# Tägliche Durchschnittswerte
sensor_data_daily_avg_view = Table(
    "sensor_data_daily_avg",
    Base.metadata,
    Column("day", DateTime(timezone=True)),
    Column("sensor_id", String(50)),
    Column("average_value", Float),
)

# Wöchentliche Durchschnittswerte
sensor_data_weekly_avg_view = Table(
    "sensor_data_weekly_avg",
    Base.metadata,
    Column("week", DateTime(timezone=True)),
    Column("sensor_id", String(50)),
    Column("average_value", Float),
)

# Monatliche Durchschnittswerte
sensor_data_monthly_avg_view = Table(
    "sensor_data_monthly_avg",
    Base.metadata,
    Column("month", DateTime(timezone=True)),
    Column("sensor_id", String(50)),
    Column("average_value", Float),
)

# Jährliche Durchschnittswerte
sensor_data_yearly_avg_view = Table(
    "sensor_data_yearly_avg",
    Base.metadata,
    Column("year", DateTime(timezone=True)),
    Column("sensor_id", String(50)),
    Column("average_value", Float),
)

# Tägliche Zusammenfassungen
sensor_data_daily_summary_agg_view = Table(
    "sensor_data_daily_summary_agg",
    Base.metadata,
    Column("day", DateTime(timezone=True)),
    Column("sensor_id", String(50)),
    Column("min_value", Float),
    Column("max_value", Float),
    Column("average_value", Float),
    Column("count", Integer), 
)
