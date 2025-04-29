-- init_db.sql

SET search_path TO public;

CREATE DATABASE prefect;

\connect umwelt;

-- 1. TimescaleDB Extension erstellen (falls nötig)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 2. Tabellen erstellen (basierend auf den SQLAlchemy-Modellen)
-- Reihenfolge beachten: sensor_box -> sensor -> sensor_data wegen Fremdschlüsseln

-- Tabelle: sensor_box
CREATE TABLE IF NOT EXISTS sensor_box (
    box_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL, 
    exposure VARCHAR(50),
    model VARCHAR(100),
    "currentLocation" JSONB, 
    "lastMeasurementAt" TIMESTAMP WITH TIME ZONE,
    last_data_fetched TIMESTAMP WITH TIME ZONE,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL,
    "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sensor_box_name ON sensor_box (name); 

-- Tabelle: sensor
CREATE TABLE IF NOT EXISTS sensor (
    sensor_id VARCHAR(50) PRIMARY KEY, 
    box_id VARCHAR(50) REFERENCES sensor_box (box_id), 
    title VARCHAR(100),
    sensor_type VARCHAR(50) NOT NULL, 
    unit VARCHAR(20) NOT NULL, 
    icon VARCHAR(50) 
);
CREATE INDEX IF NOT EXISTS idx_sensor_box_id ON sensor (box_id); -- Index für den Fremdschlüssel

-- Tabelle: sensor_data
CREATE TABLE IF NOT EXISTS sensor_data (
    id SERIAL, 
    sensor_id VARCHAR(50) REFERENCES sensor (sensor_id), 
    value DOUBLE PRECISION NOT NULL, 
    measurement_timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id, measurement_timestamp, sensor_id)
);
CREATE INDEX IF NOT EXISTS idx_sensor_data_measurement_timestamp ON sensor_data (measurement_timestamp);
CREATE INDEX IF NOT EXISTS idx_sensor_data_sensor_id ON sensor_data (sensor_id);


-- 3. sensor_data Tabelle in eine TimescaleDB Hypertable umwandeln
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'sensor_data'
    ) THEN
        RAISE INFO 'Converting sensor_data to hypertable...';
        PERFORM create_hypertable(
            'sensor_data',           
            'measurement_timestamp', 
            'sensor_id',             
            8,                       
            chunk_time_interval => INTERVAL '1 day', 
            migrate_data => TRUE     
        );
        RAISE INFO 'sensor_data converted to hypertable.';
    ELSE
        RAISE INFO 'sensor_data is already a hypertable.';
    END IF;
END
$$;

-- 4. Kontinuierliche Aggregate (Materialized Views) erstellen (basierend auf den Table-Definitionen)
CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_data_hourly_avg
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', measurement_timestamp) AS hour,
    sensor_id,
    AVG(value) AS average_value
FROM sensor_data
GROUP BY 1, 2 -- Gruppiert nach bucketed_timestamp und sensor_id
WITH NO DATA; -- Views werden initial leer erstellt und später durch den TimescaleDB Background Worker gefüllt

-- Tägliche Durchschnittswerte
CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_data_daily_avg
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', measurement_timestamp) AS day,
    sensor_id,
    AVG(value) AS average_value
FROM sensor_data
GROUP BY 1, 2
WITH NO DATA;

-- Wöchentliche Durchschnittswerte
CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_data_weekly_avg
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 week', measurement_timestamp) AS week,
    sensor_id,
    AVG(value) AS average_value
FROM sensor_data
GROUP BY 1, 2
WITH NO DATA;

-- Monatliche Durchschnittswerte
CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_data_monthly_avg
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 month', measurement_timestamp) AS month,
    sensor_id,
    AVG(value) AS average_value
FROM sensor_data
GROUP BY 1, 2
WITH NO DATA;

-- Jährliche Durchschnittswerte
CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_data_yearly_avg
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 year', measurement_timestamp) AS year,
    sensor_id,
    AVG(value) AS average_value
FROM sensor_data
GROUP BY 1, 2
WITH NO DATA;

-- Tägliche Zusammenfassungen (Min, Max, Avg, Count)
CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_data_daily_summary_agg
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', measurement_timestamp) AS day,
    sensor_id,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    AVG(value) AS average_value,
    COUNT(*) AS count
FROM sensor_data
GROUP BY 1, 2
WITH NO DATA;

-- Optional: Setze TimescaleDB Policies für die kontinuierlichen Aggregate
-- WICHTIG: start_offset - end_offset MUSS >= 2 * Bucket-Größe sein!

SELECT add_continuous_aggregate_policy('sensor_data_hourly_avg',
  start_offset => INTERVAL '3 hours', -- Beispiel: Daten älter als 3 Stunden
  end_offset => INTERVAL '1 hour',   -- Beispiel: Daten neuer als 1 Stunde (Fenster ist [start, end) )
  schedule_interval => INTERVAL '5 minutes');


SELECT add_continuous_aggregate_policy('sensor_data_daily_avg',
  start_offset => INTERVAL '3 days',
  end_offset => INTERVAL '1 day',
  schedule_interval => INTERVAL '15 minutes'); 


SELECT add_continuous_aggregate_policy('sensor_data_weekly_avg',
  start_offset => INTERVAL '3 weeks',
  end_offset => INTERVAL '1 week',
  schedule_interval => INTERVAL '1 hour'); 


SELECT add_continuous_aggregate_policy('sensor_data_monthly_avg',
  start_offset => INTERVAL '3 months',
  end_offset => INTERVAL '1 month',
  schedule_interval => INTERVAL '6 hours'); 


SELECT add_continuous_aggregate_policy('sensor_data_daily_summary_agg',
  start_offset => INTERVAL '3 days',
  end_offset => INTERVAL '1 day',
  schedule_interval => INTERVAL '15 minutes'); 
