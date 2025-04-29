# services/frontend/app/utils/api_client.py
import requests
import os
from datetime import datetime, timezone
from dash import html
import logging

logger = logging.getLogger(__name__)

from components.plot import create_time_series_graph

# Annahme: Die Backend URL kommt aus Umgebungsvariablen
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:3000") 

def get_sensor_boxes():
    """ Ruft eine Liste aller Sensorboxen vom Backend ab """
    url = f"{BACKEND_API_URL}/api/v1/sensor_boxes"
    logger.info(f"Requesting sensor boxes from backend: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status() # Wirft HTTPError für schlechte Antworten
        data = response.json()
        logger.info(f"Received data from backend (first 100 chars): {str(data)[:100]}...") 
        return data 
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching sensor boxes from backend: {e}", exc_info=True)
        raise # Fehler weitergeben


def get_aggregated_data(sensor_id: str, from_date: datetime, to_date: datetime, aggregation_params: dict):
    """
    Holt aggregierte Zeitreihendaten von deinem Backend API Endpunkt /aggregate/.
    """
    url = f"{BACKEND_API_URL}/api/v1/sensors/{sensor_id}/data/aggregate/"
    # Formatiere Datumsangaben für die API-Anfrage im RFC3339 UTC Format
    from_date_utc = from_date.astimezone(timezone.utc)
    to_date_utc = to_date.astimezone(timezone.utc)
    from_date_str = from_date_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    to_date_str = to_date_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

    params = {
        "from-date": from_date_str, 
        "to-date": to_date_str,    
        **aggregation_params 
    }

    logger.info(f"Requesting aggregated data from backend: {url} with params {params}")
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() 
        data = response.json() 
        logger.info(f"Received aggregated data from backend (first 100 chars): {str(data)[:100]}...")
        return data 
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching aggregated data from backend: {e}", exc_info=True)
        raise 

def fetch_and_create_plot_component(sensor_id: str, from_date: datetime, to_date: datetime, aggregation_params: dict):
    """
    Holt Zeitreihendaten vom Backend und erstellt eine dcc.Graph Komponente.
    """
    logger.info(f"Fetching plot data for sensor {sensor_id} from {from_date} to {to_date}.")
    try:
        plot_data_response = get_aggregated_data(sensor_id, from_date, to_date, aggregation_params) 

        if plot_data_response and 'aggregated_data' in plot_data_response and 'unit' in plot_data_response:
            aggregated_data_list = plot_data_response['aggregated_data']
            unit = plot_data_response['unit']
            aggregation_type = plot_data_response.get('aggregation_type', 'value') 

            if aggregated_data_list: 
                 logger.info(f"Received {len(aggregated_data_list)} aggregated data points.")
                 return create_time_series_graph(
                     id='main-time-series-graph', 
                     title=f"Sensor Data ({aggregation_type.capitalize()})", 
                     data=aggregated_data_list,
                     x_col='time_bucket', 
                     y_col='aggregated_value', 
                     y_axis_label=f"Value ({unit})" 
                 )
            else:
                 logger.info("API returned an empty list of aggregated data points.")
                 return html.P("Keine Daten für diesen Zeitraum gefunden.")

        else:
             logger.warning(f"API response missing expected keys: {plot_data_response}")
             return html.Div("Unerwartetes Datenformat vom Backend erhalten.", style={'color': 'red'})

    except Exception as e:
        logger.error(f"Error fetching and creating plot component: {e}", exc_info=True)
        return html.Div(f"Fehler beim Laden der Plot-Daten: {e}", style={'color': 'red'})