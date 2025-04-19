# services/frontend/app/pages/sensor_data_viz.py
import os
import sys
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State

from maindash import app
from utils import api_client 

layout = html.Div([
    html.H1("Time Series Plot"),
    # Füge hier später Bedienelemente hinzu (Sensor-Auswahl, Datumsbereich etc.)

    html.Div(id='plot-container'), # Dieses Div wird den Graphen enthalten

    # Optional: Loading Spinner für diese Seite
    # Passe die ID an, um Konflikte zu vermeiden
    dcc.Loading(id="loading-plot-data", type="default", children=html.Div(id="loading-output-plot")),
])



# Callback, der das Laden der Daten und die Erstellung des Graphen auslöst
# Dieser Callback wird ausgelöst, wenn der Inhalt des 'page-content' Divs aktualisiert wird (in app.py)
# und die aktuelle URL die von /data_viz ist.
@app.callback(Output('plot-container', 'children'), # <-- Hier wird der Graph in den plot-container geladen
              Input('page-content', 'children'), # <-- Trigger ist die Änderung des Hauptinhalts-Divs in app.py
              State('url', 'pathname'), # <-- Hole die aktuelle URL, um zu prüfen, welche Seite aktiv ist
              # Füge hier State/Input für Sensor-Auswahl und Datumsbereich hinzu, sobald Bedienelemente da sind
              prevent_initial_call=False) # Lässt den Callback beim ersten Laden der Seite auslösen
def load_plot_data_on_page_load(page_content_children, pathname): 
    logger.info(f"load_plot_data_on_page_load triggered. Pathname: {pathname}")

    # Prüfe, ob die aktuelle URL die von /data_viz ist
    if pathname == '/data_viz':
        logger.info("Pathname matches /data_viz. Calling data fetching and plot creation function.")
        # *** TODO: Die Parameter für sensor_id, from_date, to_date und aggregation_params
        # müssen von Bedienelementen auf der Seite oder aus der URL kommen ***
        default_sensor_id = '5faeb5589b2df8001b980307' 
        default_from_date = datetime(2025, 4, 19, tzinfo=timezone.utc) 
        default_to_date = datetime.now(timezone.utc) 
        default_aggregation_params = {"interval": "2m", "aggregation_type": "avg", "smoothing_window": 1, "interpolation": "linear"} 

        return api_client.fetch_and_create_plot_component(
            default_sensor_id,
            default_from_date,
            default_to_date,
            default_aggregation_params
        )
    return dash.no_update 
