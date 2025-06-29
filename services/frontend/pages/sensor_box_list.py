import os
import sys
import logging

logger = logging.getLogger(__name__)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.dcc import Download, send_data_frame
import pandas as pd

from maindash import app
from utils import api_client

# Layout
layout = layout = html.Div([
    # --- iFrame zuerst ---
    html.Div([
        html.Div([
            html.Iframe(
                src="https://opensensemap.org/explore/5faeb5589b2df8001b980304",
                className="responsive-iframe"
            )
        ], className="iframe-container"),
    ], className="content-card"),

    # --- Download-Button danach ---
    html.Div([
        html.Button(
            "Sensordaten als CSV herunterladen",
            id="download-btn",
            n_clicks=0,
            className="download-button"
        ),
        html.Div(
            dcc.Loading(
                id="loading-spinner-download",
                type="circle",
                children=html.Div(id="loading-output-download"),
                overlay_style={"width": "30px", "height": "30px"}
            ),
            style={"width": "30px", "height": "30px"}
        ),
        dcc.Download(id="download-data")
    ], className="download-section", style={"alignItems": "center", "gap": "20px"}),

    dcc.Loading(id="loading-plot-data", children=html.Div(id='plot-container')),
], className="page-container")



def load_sensor_boxes_logic():
    logger.info("Executing load_sensor_boxes_logic")
    try:
        sensor_boxes_list = api_client.get_sensor_boxes()
        logger.info(f"Received data from API in load_sensor_boxes_logic: {sensor_boxes_list}")

        if isinstance(sensor_boxes_list, list):
            if sensor_boxes_list:
                logger.info(f"Processing {len(sensor_boxes_list)} sensor boxes into HTML.")
                box_list_items = []
                for box in sensor_boxes_list:
                    if isinstance(box, dict) and 'box_id' in box and 'name' in box:
                        link = dcc.Link(f"Box: {box['name']} (ID: {box['box_id']})", href=f"/sensor_boxes/{box['box_id']}")
                        box_list_items.append(html.Li(link))
                    else:
                        logger.warning(f"Unexpected data format for sensor box item: {box}")

                if box_list_items:
                    return html.Ul(box_list_items)
                else:
                    logger.info("Processed data resulted in an empty list of items for HTML.")
                    return html.P("Keine Sensorboxen zum Anzeigen gefunden.")

            else:
                logger.info("API returned an empty list.")
                return html.P("Keine Sensorboxen gefunden.")
        else:
            logger.error(f"API returned data that is not a list (expected list): {sensor_boxes_list}")
            return html.Div("Unerwartetes Datenformat vom Backend erhalten.", style={'color': 'red'})

    except Exception as e:
        logger.error(f"Fehler in load_sensor_boxes_logic function: {e}", exc_info=True)
        return html.Div(f"Fehler beim Laden der Sensorboxen: {e}", style={'color': 'red'})


import io
import csv
import requests

@app.callback(
    # KORREKTUR: Der Callback hat jetzt zwei Outputs
    Output("download-data", "data"),
    Output("loading-output-download", "children"), # Zielt auf das leere Div im Spinner
    Input("download-btn", "n_clicks"),
    prevent_initial_call=True
)
def download_sensorboxen(n_clicks):
    try:
        # Sensor-IDs, welche dann in der CSV landen
        sensor_ids = [
            "5faeb5589b2df8001b980309",
            "5faeb5589b2df8001b980308",
            "5faeb5589b2df8001b980307",
            "5faeb5589b2df8001b980306",
            "5faeb5589b2df8001b980305"
        ]

        all_data = []

        # ... (deine Schleife zum Datenabruf bleibt exakt gleich)
        for sensor_id in sensor_ids:
            try:
                url = f"http://backend:8000/api/v1/sensors/{sensor_id}/data"
                params = {"limit": 1000000}
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        item["sensor_id"] = sensor_id
                        all_data.append(item)
                else:
                    logger.warning(f"Fehler beim Abrufen von Sensor {sensor_id}: {response.status_code}")
            except Exception as ex:
                logger.warning(f"Exception bei Sensor {sensor_id}: {ex}")

        # CSV erstellen
        if not all_data:
            # KORREKTUR: Gib ein Tupel zurück, das beide Outputs bedient
            return None, ""

        output = io.StringIO()
        fieldnames = list(all_data[0].keys())

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)
        logger.info(f"Download wird vorbereitet mit {len(all_data)} Zeilen.")

        # KORREKTUR: Gib ein Tupel zurück.
        # Der erste Wert geht an "download-data", der zweite an "loading-output-download".
        # Ein leerer String "" für den zweiten Output versteckt den Spinner wieder.
        return dict(content=output.getvalue(), filename="sensordaten.csv"), ""

    except Exception as e:
        logger.error(f"Fehler beim CSV-Export: {e}", exc_info=True)
        # Auch im Fehlerfall ein Tupel zurückgeben
        return None, "Fehler!"