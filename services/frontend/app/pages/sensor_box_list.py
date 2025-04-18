# services/frontend/app/pages/sensor_box_list.py
import os
import sys
import logging

logger = logging.getLogger(__name__)

# Beibehalten der sys.path Anpassung wie vom Benutzer gewünscht
# Dies fügt das Verzeichnis services/frontend/app/ zum Python Pfad hinzu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from dash import dcc
from dash import html
from dash.dependencies import Input, Output

# Importiere die Haupt-App Instanz
# Dies sollte jetzt funktionieren, da 'app' im sys.path gefunden wird
from app import app

# Importiere deinen API Client
# Dies sollte jetzt funktionieren, da 'utils' im sys.path gefunden wird
from utils import api_client # <-- Korrigiere den Namen

# Beispiel Layout für die Sensor Box Liste Seite
layout = html.Div([
    html.H1("Sensor Boxen"),
    html.Div(id='sensor-box-list-container'), # Hier werden die Sensorboxen angezeigt

    # Optional: Loading Spinner
    dcc.Loading(id="loading-sensor-boxes", type="default", children=html.Div(id="loading-output")),
])



# Beispiel Callback zum Laden der Sensorboxen, wenn die Seite geladen wird
@app.callback(Output('sensor-box-list-container', 'children'),
              Input('url', 'pathname')) # Trigger, wenn die URL sich ändert (und diese Seite angezeigt wird)
def load_sensor_boxes(pathname):
    logger.info("Entering load_sensor_boxes callback") # <-- Füge diese Zeile hinzu als allererstes in der Funktion
    logger.info(f"Callback load_sensor_boxes triggered with pathname: {pathname}")

    # Stelle sicher, dass dieser Callback nur auf dieser Seite ausgeführt wird
    if pathname == '/sensor_boxes':
        logger.info("Pathname matches /sensor_boxes, attempting to load data.")
        # Füge weitere Logs hinzu, um den Ablauf zu verfolgen
        logger.info("About to enter try block for data fetching.")
        try:
            logger.info("Inside try block.")
            # Daten vom Backend API abrufen
            sensor_boxes_list = api_client.get_sensor_boxes()
            logger.info(f"Received data from API: {sensor_boxes_list}")
            # ... (restliche Logik und Logs im try Block) ...

        except Exception as e:
            logger.error(f"Error caught in try block: {e}", exc_info=True)
            # ... (restliche Fehlerbehandlung) ...
            return html.Div(f"Fehler beim Laden der Sensorboxen: {e}", style={'color': 'red'}) # Stelle sicher, dass der Fehler hier zurückgegeben wird

    else:
        # Gebe None zurück, wenn der Callback auf einer anderen Seite getriggert wird
        return None