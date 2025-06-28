import os
import sys
import logging
import re
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go

logger = logging.getLogger(__name__)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import dcc, html
from dash.dependencies import Input, Output

from maindash import app
from utils import api_client

BOX_ID = "5faeb5589b2df8001b980304"

# Sensor-Optionen beim Start der App laden
try:
    sensors = api_client.get_sensors_for_box(BOX_ID)
    sensor_options = [
        {"label": s.get("title", "Sensor"), "value": s["sensor_id"]}
        for s in sensors
    ]
    default_sensor = next(
        (s for s in sensor_options if s["label"].lower() == "temperatur"),
        sensor_options[0] if sensor_options else None,
    )
    default_sensor_value = default_sensor["value"] if default_sensor else None
except Exception as e:
    logger.error("Fehler beim Abrufen der Sensoren: %s", e)
    sensor_options = []
    default_sensor_value = None

# ---------------------------------------------------------------
# Intervall – default und Validierung
# ---------------------------------------------------------------
DEFAULT_INTERVAL_VALUE = "12h"  # kann vom User überschrieben werden
# Einfache Regex: Zahl + Einheit (s|m|h|d|w)
INTERVAL_PATTERN = re.compile(r"^\s*\d+\s*[smhdw]\s*$", re.IGNORECASE)

# --- Dashboard-Layout ---
layout = html.Div(
    [
        html.Div(
            className="dashboard-container",
            children=[
                # --- LINKE SEITENLEISTE (SIDEBAR) ---
                html.Div(
                    className="sidebar",
                    children=[
                        html.H2("Steuerung"),

                        # Zeitraum
                        html.Div(
                            className="control-group",
                            children=[
                                html.Label("Zeitraum"),
                                dcc.DatePickerRange(
                                    id="date-range-picker",
                                    start_date=(datetime.now() - timedelta(days=30)).date(),
                                    end_date=datetime.now().date(),
                                    display_format="DD.MM.YYYY",
                                    style={"width": "100%"},
                                ),
                            ],
                        ),

                        # Sensor
                        html.Div(
                            className="control-group",
                            children=[
                                html.Label("Sensor"),
                                dcc.Dropdown(
                                    id="sensor-dropdown",
                                    options=sensor_options,
                                    value=default_sensor_value,
                                    clearable=False,
                                ),
                            ],
                        ),

                        # Freie Intervall-Eingabe
                        html.Div(
                            className="control-group",
                            children=[
                                html.Label("Intervall (z. B. 15m, 2h, 1d)"),
                                dcc.Input(
                                    id="interval-input",
                                    type="text",
                                    value=DEFAULT_INTERVAL_VALUE,
                                    debounce=True,  # erst beim Verlassen des Feldes auslösen
                                    placeholder="z.B. 12h",
                                    style={"width": "100%"},
                                ),
                            ],
                        ),

                        # Glättung
                        html.Div(
                            className="control-group",
                            children=[
                                html.Label("Kurvenglättung (Fenstergröße)"),
                                dcc.Slider(
                                    id="smoothing-slider",
                                    min=1,
                                    max=20,
                                    step=1,
                                    value=3,
                                    marks={i: str(i) for i in range(1, 21)},
                                ),
                            ],
                        ),
                    ],
                ),

                # --- RECHTER HAUPTBEREICH ---
                html.Div(
                    className="main-content",
                    children=[
                        dcc.Loading(
                            id="loading-plot-data",
                            type="graph",
                            parent_style={
                                "height": "100%",
                                "width": "100%",
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "center",
                            },
                            children=html.Div(
                                id="plot-container",
                                style={"height": "100%", "width": "100%"},
                            ),
                        )
                    ],
                ),
            ],
        )
    ]
)

# -------------------------------------
# Callback für das Aktualisieren des Plots
# -------------------------------------
@app.callback(
    Output("plot-container", "children"),
    Input("sensor-dropdown", "value"),
    Input("date-range-picker", "start_date"),
    Input("date-range-picker", "end_date"),
    Input("smoothing-slider", "value"),
    Input("interval-input", "value"),
)

def update_plot(sensor_id, start_date, end_date, smoothing_value, interval_value):
    """Aktualisiert den Plot basierend auf Benutzereingaben."""
    if not all([sensor_id, start_date, end_date]):
        return html.P("Bitte wähle einen Sensor und einen Zeitraum aus.")

    # Intervall validieren
    if not interval_value or not INTERVAL_PATTERN.match(interval_value):
        return html.P(
            "Ungültiges Intervall. Bitte gib z. B. 15m, 2h, 1d oder 1w ein.",
            style={"color": "red"},
        )

    interval_value = interval_value.strip().lower()

    try:
        from_date = datetime.fromisoformat(start_date)
        to_date = datetime.fromisoformat(end_date)
    except ValueError:
        return html.P("Ungültiges Datumsformat.")

    # Parameter für die Aggregation
    aggregation_params = {
        "interval": interval_value,
        "aggregation_type": "avg",
        "smoothing_window": smoothing_value,
        "interpolation": "linear",
    }

    try:
        response = api_client.get_aggregated_data(
            sensor_id, from_date, to_date, aggregation_params
        )

        if not response or not response.get("aggregated_data"):
            return html.Div("Keine Daten für den ausgewählten Zeitraum verfügbar.")

        df = pd.DataFrame(response["aggregated_data"])
        unit = response.get("unit", "")
        sensor_title = next(
            (s["label"] for s in sensor_options if s["value"] == sensor_id),
            "Sensor",
        )

        # Kennzahlen
        max_val = df["aggregated_value"].max()
        min_val = df["aggregated_value"].min()
        avg_val = df["aggregated_value"].mean()

        # Linien-Plot
        fig = go.Figure(
            go.Scatter(
                x=df["time_bucket"],
                y=df["aggregated_value"],
                mode="lines",
                name=sensor_title,
                line=dict(width=2,color = "#4CAF50"),
            )
        )

        fig.update_layout(
            title=f"Verlauf für: <b>{sensor_title}</b>",
            xaxis_title=None,
            yaxis_title=f"Wert ({unit})",
            margin=dict(l=40, r=20, t=50, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#fdfdff",
            height=None,
        )

        return [
            html.Div(
                dcc.Graph(figure=fig, style={"height": "100%"}),
                className="graph-container",
            ),
            html.Div(
                [
                    # Maximalwert
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Img(
                                        src=app.get_asset_url("icons/arrow-up.svg"),
                                        className="stat-icon",
                                    ),
                                    html.P("Maximalwert", className="stat-title"),
                                ],
                                className="stat-title-container",
                            ),
                            html.P(f"{max_val:.2f} {unit}", className="stat-value"),
                        ],
                        className="stat-card",
                    ),
                    # Minimalwert
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Img(
                                        src=app.get_asset_url("icons/arrow-down.svg"),
                                        className="stat-icon",
                                    ),
                                    html.P("Minimalwert", className="stat-title"),
                                ],
                                className="stat-title-container",
                            ),
                            html.P(f"{min_val:.2f} {unit}", className="stat-value"),
                        ],
                        className="stat-card",
                    ),
                    # Durchschnitt
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Img(
                                        src=app.get_asset_url("icons/bar-chartb.svg"),
                                        className="stat-icon",
                                    ),
                                    html.P("Durchschnitt", className="stat-title"),
                                ],
                                className="stat-title-container",
                            ),
                            html.P(f"{avg_val:.2f} {unit}", className="stat-value"),
                        ],
                        className="stat-card",
                    ),
                ],
                className="stats-container",
            ),
        ]

    except Exception as e:
        logger.error("Fehler beim Laden der Plot-Daten: %s", e, exc_info=True)
        return html.Div(
            f"Fehler beim Laden der Plot-Daten: {str(e)}", style={"color": "red"}
        )