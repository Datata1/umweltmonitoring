# services/backend/app/crud/crud_sensor.py
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc, func, case, column, over, text, alias

from .models import SensorBox, Sensor, SensorData
from .models import sensor_data_hourly_avg_view, sensor_data_daily_avg_view, \
                              sensor_data_weekly_avg_view, sensor_data_monthly_avg_view, \
                              sensor_data_yearly_avg_view, sensor_data_daily_summary_agg_view
from .sensor import SensorBoxCreate, SensorBoxUpdate, SensorCreate, SensorUpdate, SensorDataCreate

class CRUDSensorBox:
    def get(self, db: Session, id: str) -> Optional[SensorBox]:
        return db.query(SensorBox).filter(SensorBox.box_id == id).first()

    # Fehlende Methode hinzugefügt
    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[SensorBox]:
        """
        Ruft mehrere Sensorboxen ab.
        """
        return db.query(SensorBox).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: SensorBoxCreate) -> SensorBox:
        db_obj = SensorBox(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: SensorBox, obj_in: SensorBoxUpdate) -> SensorBox:
        update_data = obj_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_obj, key, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


class CRUDSensor:
    def get(self, db: Session, id: str) -> Optional[Sensor]:
        return db.query(Sensor).filter(Sensor.sensor_id == id).first()

    # Fehlende Methode hinzugefügt
    def get_multi_by_box_id(self, db: Session, *, box_id: str, skip: int = 0, limit: int = 100) -> List[Sensor]:
        """
        Ruft alle Sensoren für eine spezifische Sensorbox ab.
        """
        return db.query(Sensor).filter(Sensor.box_id == box_id).offset(skip).limit(limit).all()


    def create(self, db: Session, *, obj_in: SensorCreate) -> Sensor:
        db_obj = Sensor(
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

    def update(self, db: Session, *, db_obj: Sensor, obj_in: SensorUpdate) -> Sensor:
        update_data = obj_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_obj, key, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


class CRUDSensorData:
    def create_multi(self, db: Session, *, objs_in: List[SensorDataCreate]) -> List[SensorData]:
        db_objs = (SensorData(**obj_in.model_dump()) for obj_in in objs_in)
        db.bulk_save_objects(db_objs)
        db.commit()
        return list(db_objs)

    def get_by_sensor_id(
        self,
        db: Session,
        *,
        sensor_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 1000 
    ) -> List[SensorData]:
        """
        Ruft Datenpunkte für einen spezifischen Sensor ab, optional innerhalb eines Zeitraums.
        """
        query = db.query(SensorData).filter(SensorData.sensor_id == sensor_id)

        if from_date:
            query = query.filter(SensorData.measurement_timestamp >= from_date)
        if to_date:
            query = query.filter(SensorData.measurement_timestamp <= to_date)

        # Standardmäßig nach Zeit absteigend sortieren, um die neuesten Daten zuerst zu bekommen
        query = query.order_by(desc(SensorData.measurement_timestamp))

        return query.offset(skip).limit(limit).all()
    
    def get_hourly_average_by_sensor_id(
        self,
        db: Session,
        *,
        sensor_id: str,
        from_date: datetime,
        to_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Ruft stündliche Durchschnittswerte aus der kontinuierlichen Aggregation ab.
        """
        query = db.query(
            sensor_data_hourly_avg_view.c.hour.label('hour'),
            sensor_data_hourly_avg_view.c.average_value.label('average_value')
        ) \
        .filter(sensor_data_hourly_avg_view.c.sensor_id == sensor_id)  \
        .filter(sensor_data_hourly_avg_view.c.hour >= from_date)  \
        .filter(sensor_data_hourly_avg_view.c.hour < to_date)  \
        .order_by(sensor_data_hourly_avg_view.c.hour)

        results = query.all()

        return [row._asdict() for row in results]
    

    def get_daily_summary_by_sensor_id(
        self,
        db: Session,
        *,
        sensor_id: str,
        from_date: datetime,
        to_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Ruft tägliche Zusammenfassungen aus der kontinuierlichen Aggregation ab.
        """
        query = db.query(
            sensor_data_daily_summary_agg_view.c.day.label('time_bucket'), # Label ist 'time_bucket' in query result
            sensor_data_daily_summary_agg_view.c.min_value.label('min_value'),
            sensor_data_daily_summary_agg_view.c.max_value.label('max_value'),
            sensor_data_daily_summary_agg_view.c.average_value.label('average_value'),
            sensor_data_daily_summary_agg_view.c.count.label('count')
        ) \
        .filter(sensor_data_daily_summary_agg_view.c.sensor_id == sensor_id)  \
        .filter(sensor_data_daily_summary_agg_view.c.day >= from_date)  \
        .filter(sensor_data_daily_summary_agg_view.c.day < to_date)  \
        .order_by(sensor_data_daily_summary_agg_view.c.day)

        results = query.all()

        return [{
            'day': row.time_bucket, 
            'min_value': row.min_value,
            'max_value': row.max_value,
            'average_value': row.average_value,
            'count': row.count
        } for row in results]
    
    def get_statistics_by_sensor_id(
        self,
        db: Session,
        *,
        sensor_id: str,
        from_date: datetime,
        to_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Ruft statistische Kennzahlen (Avg, Min, Max, Count, StdDev) für einen spezifischen Sensor in einem Zeitraum ab.
        Gibt ein einzelnes Dictionary zurück.
        """
        result = db.query(
            func.avg(SensorData.value).label('average_value'),
            func.min(SensorData.value).label('min_value'),
            func.max(SensorData.value).label('max_value'),
            func.count(SensorData.id).label('count'),
            func.stddev(SensorData.value).label('stddev_value') 
        ) \
        .filter(SensorData.sensor_id == sensor_id) \
        .filter(SensorData.measurement_timestamp >= from_date) \
        .filter(SensorData.measurement_timestamp < to_date) \
        .one_or_none() 

        if result:
            stats_data = result._asdict()
            stats_data['average_value'] = float(stats_data['average_value']) if stats_data['average_value'] is not None else None
            stats_data['min_value'] = float(stats_data['min_value']) if stats_data['min_value'] is not None else None
            stats_data['max_value'] = float(stats_data['max_value']) if stats_data['max_value'] is not None else None
            stats_data['stddev_value'] = float(stats_data['stddev_value']) if stats_data['stddev_value'] is not None else None

            return stats_data
        else:
            return {"average_value": None, "min_value": None, "max_value": None, "count": 0, "stddev_value": None}


    def get_aggregated_data_by_sensor_id(
        self,
        db: Session,
        *,
        sensor_id: str,
        from_date: datetime,
        to_date: datetime,
        interval: str, # Z.B. '1 hour', '1 day', '5 minutes'
        aggregation_type: str, # Z.B. 'avg', 'min', 'max', 'count', 'sum'
        smoothing_window: Optional[int] = None, # Optional: Fenstergröße für Glättung auf aggregierten Daten
        interpolation_method: Optional[str] = None # Optional: 'linear', 'locf'
    ) -> List[Dict[str, Any]]:
        """
        Ruft aggregierte Daten mit flexiblem Intervall/Typ ab, wendet optional Glättung und/oder Interpolation an.
        """
        allowed_aggregation_types = ['avg', 'min', 'max', 'count', 'sum']
        if aggregation_type.lower() not in allowed_aggregation_types:
            raise ValueError(f"Ungültiger Aggregationstyp: {aggregation_type}. Erlaubt: {allowed_aggregation_types}")

        if smoothing_window is not None and smoothing_window <= 0:
             raise ValueError("smoothing_window muss größer als 0 sein.")

        allowed_interpolation_methods = ['linear', 'locf'] # TimescaleDB spezifische Methoden
        if interpolation_method is not None and interpolation_method.lower() not in allowed_interpolation_methods:
            raise ValueError(f"Ungültige Interpolationsmethode: {interpolation_method}. Erlaubt: {allowed_interpolation_methods}")

        agg_func = None
        if aggregation_type.lower() == 'avg':
            agg_func = func.avg(SensorData.value)
        elif aggregation_type.lower() == 'min':
            agg_func = func.min(SensorData.value)
        elif aggregation_type.lower() == 'max':
            agg_func = func.max(SensorData.value)
        elif aggregation_type.lower() == 'count':
            agg_func = func.count(SensorData.id)
        elif aggregation_type.lower() == 'sum':
             agg_func = func.sum(SensorData.value)

        if agg_func is None:
             raise ValueError(f"Ungültiger Aggregationstyp nach Validierung: {aggregation_type}")


        # Schritt 1: Aggregation und optionales Gapfilling
        time_bucket_func = func.time_bucket_gapfill if interpolation_method is not None else func.time_bucket

        aggregated_cte = db.query(
            time_bucket_func(text(f"INTERVAL '{interval}'"), SensorData.measurement_timestamp).label('time_bucket'),
            agg_func.label('aggregated_value_raw'),
            func.count(SensorData.id).label('count') 
        ) \
        .filter(SensorData.sensor_id == sensor_id) \
        .filter(SensorData.measurement_timestamp >= from_date) \
        .filter(SensorData.measurement_timestamp < to_date) \
        .group_by('time_bucket') \
        .order_by('time_bucket')

        # Wenn Gapfilling, füge die Range zu time_bucket_gapfill hinzu
        if interpolation_method is not None:
            aggregated_cte = aggregated_cte.filter(
                text(f"time_bucket(INTERVAL '{interval}', measurement_timestamp) >= '{from_date.isoformat()}' AND time_bucket(INTERVAL '{interval}', measurement_timestamp) < '{to_date.isoformat()}'")
            )

        aggregated_cte = aggregated_cte.cte("aggregated_data")

        # Schritt 2: Optionale Interpolation und/oder Glättung auf den aggregierten Daten
        query = db.query(
             aggregated_cte.c.time_bucket.label('time_bucket'),
             aggregated_cte.c.count.label('count') # Behalte die Anzahl
        )

        # Wende Interpolation an, wenn gewünscht
        interpolated_value = aggregated_cte.c.aggregated_value_raw
        if interpolation_method is not None:
             if interpolation_method.lower() == 'linear':
                 interpolated_value = func.interpolate(aggregated_cte.c.aggregated_value_raw)
             elif interpolation_method.lower() == 'locf':
                 interpolated_value = func.locf(aggregated_cte.c.aggregated_value_raw)


        # Wende Glättung auf den (potenziell interpolierten) Wert an, wenn gewünscht
        final_value = interpolated_value 
        if smoothing_window is not None:
             frame_boundary = (smoothing_window - 1) // 2
             final_value = func.avg(interpolated_value).over(
                order_by=aggregated_cte.c.time_bucket,
                rows=(-frame_boundary, frame_boundary)
             )

        query = query.add_columns(final_value.label('aggregated_value'))

        # Führe die Query auf der CTE aus
        results = query.select_from(aggregated_cte).all()

        return [row._asdict() for row in results]


# exports 
# FIXME: refactor this maybe?
sensor_box = CRUDSensorBox()
sensor = CRUDSensor()
sensor_data = CRUDSensorData()