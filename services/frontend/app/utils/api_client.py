# services/frontend/app/utils/api_client.py
import requests
import os
import logging
from datetime import datetime
from dash import html

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
        logger.info(f"Received data from backend (first 100 chars): {str(data)[:100]}...") # Logge nur einen Teil der Daten
        return data # Rückgabe der Daten (erwartet wird eine Liste durch response_model)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching sensor boxes from backend: {e}", exc_info=True)
        raise # Fehler weitergeben


def get_aggregated_data(sensor_id: str, from_date: datetime, to_date: datetime, aggregation_params: dict):
    """
    Holt aggregierte Zeitreihendaten von deinem Backend API Endpunkt /aggregate/.
    """
    url = f"{BACKEND_API_URL}/api/v1/sensors/{sensor_id}/data/aggregate/"
    # Formatiere Datumsangaben für die API-Anfrage im RFC3339 UTC Format
    from_date_str = from_date.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    to_date_str = to_date.isoformat(timespec='milliseconds').replace('+00:00', 'Z')

    params = {
        "from-date": from_date_str, # Query Parameter Name vom Backend Endpunkt
        "to-date": to_date_str,     # Query Parameter Name vom Backend Endpunkt
        **aggregation_params # Füge die anderen Parameter wie interval, aggregation_type, smoothing, interpolation hinzu
    }

    logger.info(f"Requesting aggregated data from backend: {url} with params {params}")
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # Wirft HTTPError für schlechte Antworten
        # Erwartet ein Dictionary mit 'unit', 'aggregation_type', 'interval', 'aggregated_data'
        data = response.json() 
        logger.info(f"Received aggregated data from backend (first 100 chars): {str(data)[:100]}...")
        return data # Gibt das erhaltene Dictionary zurück
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching aggregated data from backend: {e}", exc_info=True)
        raise # Fehler weitergeben

def fetch_and_create_plot_component(sensor_id: str, from_date: datetime, to_date: datetime, aggregation_params: dict):
    """
    Holt Zeitreihendaten vom Backend und erstellt eine dcc.Graph Komponente.
    """
    logger.info(f"Fetching plot data for sensor {sensor_id} from {from_date} to {to_date}.")
    try:
        # Daten vom Backend API abrufen (Aufruf deiner Backend-Endpunkte)
        # Annahme: api_client.get_aggregated_data existiert und ruft deinen /aggregate/ Endpunkt auf
        plot_data_response = get_aggregated_data(sensor_id, from_date, to_date, aggregation_params) 

        # Das Backend sollte ein Dictionary mit 'unit', 'aggregation_type', 'interval', 'aggregated_data' zurückgeben
        if plot_data_response and 'aggregated_data' in plot_data_response and 'unit' in plot_data_response:
            aggregated_data_list = plot_data_response['aggregated_data']
            unit = plot_data_response['unit']
            aggregation_type = plot_data_response.get('aggregation_type', 'value') # Standardlabel falls fehlt

            if aggregated_data_list: # Prüfe, ob die Liste der Datenpunkte nicht leer ist
                 logger.info(f"Received {len(aggregated_data_list)} aggregated data points.")
                 # Erstelle die Graphen-Komponente mit den abgerufenen Daten
                 return create_time_series_graph(
                     id='main-time-series-graph', # Eindeutige ID für die Komponente
                     title=f"Sensor Data ({aggregation_type.capitalize()})", # Titel aus Aggregationstyp
                     data=aggregated_data_list,
                     x_col='time_bucket', # Spaltenname im aggregierten Ergebnis (aus deinem Schema)
                     y_col='aggregated_value', # Spaltenname im aggregierten Ergebnis (aus deinem Schema)
                     y_axis_label=f"Value ({unit})" # Label mit Einheit
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