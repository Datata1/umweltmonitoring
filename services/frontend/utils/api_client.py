# services/frontend/app/utils/api_client.py
import requests
import os
from datetime import datetime, timezone
from dash import html
import logging

logger = logging.getLogger(__name__)

from components.plot import create_time_series_graph

# Annahme: Die Backend URL kommt aus Umgebungsvariablen
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://backend:3000") 

def get_sensor_boxes():
    """Ruft eine Liste aller Sensorboxen vom Backend ab"""
    url = f"{BACKEND_API_URL}/api/v1/sensor_boxes"
    logger.info(f"Requesting sensor boxes from backend: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Received {len(data)} sensor boxes from backend")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching sensor boxes from backend: {e}", exc_info=True)
        raise

def get_sensors_for_box(box_id: str):
    """Ruft alle Sensoren einer spezifischen Sensorbox ab"""
    url = f"{BACKEND_API_URL}/api/v1/sensor_boxes/{box_id}/sensors"
    logger.info(f"Requesting sensors for box {box_id} from backend: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Received {len(data)} sensors for box {box_id}")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching sensors for box {box_id}: {e}", exc_info=True)
        raise

def get_aggregated_data(sensor_id: str, from_date: datetime, to_date: datetime, aggregation_params: dict):
    """Holt aggregierte Zeitreihendaten für einen spezifischen Sensor"""
    url = f"{BACKEND_API_URL}/api/v1/sensors/{sensor_id}/data/aggregate/"
    from_date_utc = from_date.astimezone(timezone.utc)
    to_date_utc = to_date.astimezone(timezone.utc)
    params = {
        "from-date": from_date_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "to-date": to_date_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
        **aggregation_params
    }
    logger.info(f"Requesting aggregated data for sensor {sensor_id}")
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching aggregated data for sensor {sensor_id}: {e}", exc_info=True)
        raise

def fetch_and_create_plot_component(sensor_id: str, from_date: datetime, to_date: datetime, aggregation_params: dict):
    """Holt Daten und erstellt Plot-Komponente"""
    logger.info(f"Creating plot for sensor {sensor_id}")
    try:
        plot_data = get_aggregated_data(sensor_id, from_date, to_date, aggregation_params)
        
        if not plot_data or 'aggregated_data' not in plot_data:
            logger.warning(f"No data found for sensor {sensor_id}")
            return html.P("Keine Daten für diesen Zeitraum gefunden.")
            
        return create_time_series_graph(
            id='sensor-data-plot',
            title=f"Sensor {sensor_id} Data",
            data=plot_data['aggregated_data'],
            x_col='time_bucket',
            y_col='aggregated_value',
            y_axis_label=plot_data.get('unit', 'Value')
        )
    except Exception as e:
        logger.error(f"Plot creation failed for sensor {sensor_id}: {e}")
        return html.Div(f"Fehler beim Erstellen des Plots: {str(e)}", style={'color': 'red'})
    
def get_predictions():
    """Ruft die kombinierten historischen Daten und die Vorhersagen ab."""
    url = f"{BACKEND_API_URL}/api/v1/predictions"
    logger.info(f"Requesting predictions from: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching predictions from backend: {e}", exc_info=True)
        raise

def get_models():
    """Ruft die Metadaten aller trainierten Modelle ab."""
    url = f"{BACKEND_API_URL}/api/v1/models"
    logger.info(f"Requesting models from: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching models from backend: {e}", exc_info=True)
        raise