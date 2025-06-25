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
layout = html.Div([
    html.H1("Sensor Boxen", style={"textAlign": "center"}),

    dcc.Loading(
        id="loading-plot-data",
        type="graph",
        fullscreen=False,
        children=html.Div(id='plot-container'),
        className="loading-container"
    ),

    html.H2("Wo ist unsere SenseBox und welche Werte werden gemessen?", style={"textAlign": "center"}),

    html.Div([
        html.Iframe(
            src="https://opensensemap.org/explore/5faeb5589b2df8001b980304",
            width="1280",
            height="960",
            style={"border": "0", "display": "block", "marginLeft": "auto", "marginRight": "auto"}
        )
    ]),

    html.Div([
        html.Button(
            "Sensorbox Daten als CSV herunterladen",
            id="download-btn",
            n_clicks=0,
            style={
                "backgroundColor": "#4CAF50",
                "color": "white",
                "padding": "12px 24px",
                "fontSize": "16px",
                "border": "none",
                "borderRadius": "8px",
                "cursor": "pointer",
                "boxShadow": "2px 2px 10px rgba(0,0,0,0.1)"
            }
        ),
        Download(id="download-data")
    ], style={
        "display": "flex",
        "justifyContent": "center",
        "marginTop": "60px"
    }),

    html.Div(style={"marginTop": "50px"}),

    html.H3("Wie funktioniert eine SenseBox?", style={"textAlign": "center"}),

    html.Div([
        html.Img(src="assets/senseBox.png", style={
            "display": "block",
            "marginLeft": "auto",
            "marginRight": "auto",
            "maxWidth": "60%",
            "height": "auto"
        })
    ], style={"textAlign": "center"}),
    html.Div(style={"height": "200px"})
], style={
    "height": "100vh",
    "overflowY": "scroll",
    "overflowX": "hidden"
})



# Callback zum Laden der Sensorboxenliste
@app.callback(
    Output('sensor-box-list-container', 'children'),
    Input('page-content', 'children'),
    State('url', 'pathname'),
    prevent_initial_call=False
)
def trigger_data_load_for_sensor_box_list(page_content_children, pathname):
    logger.info(f"trigger_data_load_for_sensor_box_list triggered. Pathname: {pathname}")
    if pathname == '/sensor_boxes':
        logger.info("Pathname matches /sensor_boxes. Calling load_sensor_boxes function to fetch data.")
        return load_sensor_boxes_logic() 
    return dash.no_update


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
    Output("download-data", "data"),
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

        for sensor_id in sensor_ids:
            try:
                url = f"http://backend:8000/api/v1/sensors/{sensor_id}/data"
                response = requests.get(url)
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
            return None

        output = io.StringIO()
        fieldnames = list(all_data[0].keys())

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)
        logger.info(f"Download wird vorbereitet mit {len(all_data)} Zeilen.")

        return dict(content=output.getvalue(), filename="sensordaten.csv")

    except Exception as e:
        logger.error(f"Fehler beim CSV-Export: {e}", exc_info=True)
        return None