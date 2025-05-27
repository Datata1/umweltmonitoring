# services/frontend/app/pages/sensor_box_list.py
import os
import sys
import logging

logger = logging.getLogger(__name__)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State

from maindash import app
from utils import api_client

# Layout
layout = html.Div([
    html.H1("Sensor Boxen"),

    html.Div(id='sensor-box-list-container'),

    dcc.Loading(
        id="loading-plot-data",
        type="graph",
        fullscreen=False,
        children=html.Div(id='plot-container'),
        className="loading-container"
    ),

    html.H3("Wie funktioniert eine SenseBox?"),
    html.Img(src="assets/senseBox.png", style={"width": "60%", "margin-bottom": "20px"}),

    html.H2("Standortkarte"),

    html.Iframe(
        src="https://opensensemap.org/explore/5faeb5589b2df8001b980304",
        width="1200",
        height="900",
        style={"border": "0"}
    ),
    html.Div(style={"marginTop": "250px"})

], style={"height": "100vh",           
    "overflowY": "scroll",  
    "overflowX": "hidden"})

# Callback
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
    logger.info("Executing load_sensor_boxes_logic (defined in callbacks/sensor_box_list_callbacks.py)")
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