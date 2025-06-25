# services/frontend/app/pages/sensor_data_viz.py
import os
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

logger = logging.getLogger(__name__)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State

from maindash import app
from utils import api_client 

BOX_ID = "5faeb5589b2df8001b980304"

sensor_options = []
default_sensor_value = None

try:
    sensors = api_client.get_sensors_for_box(BOX_ID)  # Neue Funktion verwenden
    sensor_options = [
        {"label": s.get("title", "Sensor"), "value": s["sensor_id"]}
        for s in sensors
    ]

    # "Temperatur" als Default wählen, wenn vorhanden
    for option in sensor_options:
        if option["label"].lower() == "temperatur":
            default_sensor_value = option["value"]
            break

    if default_sensor_value is None and sensor_options:
        default_sensor_value = sensor_options[0]["value"]

except Exception as e:
    logger.error(f"Fehler beim Abrufen der Sensoren für Box {BOX_ID}: {e}")
    sensor_options = []
    default_sensor_value = None


layout = html.Div([
    html.H1("Time Series Plot"),

    # Zeitraum-Auswahl
    html.Div([
        html.Label("Zeitraum auswählen"),
        dcc.DatePickerRange(
            id='date-range-picker',
            start_date=(datetime.now() - timedelta(days=7)).date(),
            end_date=datetime.now().date(),
            display_format='DD.MM.YYYY',
            minimum_nights=0,
            clearable=True
        )
    ], style={'padding': '20px'}),

    # Sensor Dropdown
    html.Div([
        html.Label("Sensor auswählen"),
        dcc.Dropdown(
            id='sensor-dropdown',
            options=sensor_options,
            value=default_sensor_value,  # Hier setzen wir "Temperatur" vorausgewählt
            clearable=False,
            style={"width": "300px"})
    ], style={'padding': '20px'}),

    # Glättung Slider
    html.Div([
        html.Label("Kurvenglättung (Fenstergröße)"),
        dcc.Slider(
            id='smoothing-slider',
            min=0,
            max=10,
            step=1,
            value=3,
            marks={i: str(i) for i in range(0, 11)},
            tooltip={"placement": "bottom", "always_visible": True}
        )
    ], style={'padding': '20px'}),

    # Ladeanzeige + Plot Container
    dcc.Loading(
        id="loading-plot-data",
        type="graph",
        fullscreen=False,
        children=html.Div(id='plot-container'),
        className="loading-container"
    )
])

# Callback aktualisiert Plot basierend auf Sensor, Zeitraum, Glättung und Pfad
@app.callback(
    Output('plot-container', 'children'),
    Input('sensor-dropdown', 'value'),
    Input('date-range-picker', 'start_date'),
    Input('date-range-picker', 'end_date'),
    Input('smoothing-slider', 'value'),
    State('url', 'pathname'),
    prevent_initial_call=False
)
def update_plot_based_on_date_and_smoothing(sensor_id, start_date, end_date, smoothing_value, pathname):
    logger.info(f"Callback triggered – Sensor: {sensor_id}, Start: {start_date}, End: {end_date}, Smoothing: {smoothing_value}, Path: {pathname}")

    if pathname != '/data_viz' or not start_date or not end_date or not sensor_id:
        return dash.no_update

    from_date = datetime.fromisoformat(start_date)
    to_date = datetime.fromisoformat(end_date)

    aggregation_params = {
        "interval": "1h",
        "aggregation_type": "avg",
        "smoothing_window": smoothing_value,
        "interpolation": "linear"
    }

    try:
        plot_data_response = api_client.get_aggregated_data(sensor_id, from_date, to_date, aggregation_params)

        if plot_data_response and 'aggregated_data' in plot_data_response and 'unit' in plot_data_response:
            aggregated_data_list = plot_data_response['aggregated_data']
            unit = plot_data_response['unit']

            if not aggregated_data_list:
                return html.Div("Keine Daten verfügbar.")

            df = pd.DataFrame(aggregated_data_list)
            max_val = df['aggregated_value'].max()
            min_val = df['aggregated_value'].min()
            avg_val = df['aggregated_value'].mean()

            fig = px.line(df, x='time_bucket', y='aggregated_value', title='Sensorwerte')

            return html.Div([
                dcc.Graph(figure=fig),
                html.Div([
                    html.P(f"🔺 Max: {max_val:.2f} {unit}"),
                    html.P(f"🔻 Min: {min_val:.2f} {unit}"),
                    html.P(f"📊 Durchschnitt: {avg_val:.2f} {unit}"),
                ], style={
                    "marginTop": "20px",
                    "backgroundColor": "#f0f0f0",
                    "padding": "15px",
                    "borderRadius": "10px"
                })
            ])
        else:
            return html.Div("Unerwartetes Datenformat vom Backend erhalten.", style={'color': 'red'})
    except Exception as e:
        logger.error(f"Fehler beim Laden der Plot-Daten: {e}")
        return html.Div(f"Fehler beim Laden der Plot-Daten: {e}", style={'color': 'red'})