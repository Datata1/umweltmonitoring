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
#import matplotlib.pyplot as plt
#from statsmodels.tsa.arima.model import ARIMA


from maindash import app
from utils import api_client

# Layout
layout = html.Div(
    style={
        "height": "100vh",           # Volle Höhe des Viewports
        "overflowY": "auto",         # Vertikaler Scrollbalken bei Bedarf
        "padding": "20px",           # Optional: Etwas Innenabstand für schönere Darstellung
        "boxSizing": "border-box"    # Padding wird bei der Höhe berücksichtigt
    },
    children=[
        html.H1("Vorhersagen", style={"textAlign": "center"}),

        dcc.Loading(
            id="loading-plot-data",
            type="graph",
            fullscreen=False,
            children=dcc.Graph(id='time-series-plot'),
            className="loading-container"
        ),

        html.H2("Wo ist unsere SenseBox und welche Werte werden gemessen?", style={"textAlign": "center"}),

        html.Iframe(
            src="https://opensensemap.org/explore/5faeb5589b2df8001b980304",
            width="1280",
            height="960",
            style={"border": "0", "display": "block", "marginLeft": "auto", "marginRight": "auto"}
        ),

        dcc.Interval(
            id='interval-component',
            interval=5*60*1000,
            n_intervals=0
        )
    ]
)


# Callback zur Aktualisierung des Plots
@app.callback(
    Output('time-series-plot', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_plot(n_intervals):
    # CSV-Datei laden
    df = pd.read_csv("assets/sensordaten.csv")

    # Zeitstempel verarbeiten und sortieren
    df['measurement_timestamp'] = pd.to_datetime(df['measurement_timestamp'])
    df = df.sort_values('measurement_timestamp')

    # Zeitreihe vorbereiten
    df_ts = df[['measurement_timestamp', 'value']].set_index('measurement_timestamp')
    df_ts = df_ts.groupby('measurement_timestamp').mean()
    df_ts = df_ts.resample('1T').mean()
    df_ts = df_ts.interpolate(method='time')

    # ARIMA-Modell trainieren
    model = ARIMA(df_ts, order=(1, 1, 1))
    model_fit = model.fit()

    # Vorhersage der nächsten 20 Minuten
    forecast_steps = 20
    forecast = model_fit.forecast(steps=forecast_steps)

    # Plotly-Figure erstellen
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_ts.index[-100:], y=df_ts['value'][-100:], mode='lines', name='Historische Werte'))
    fig.add_trace(go.Scatter(
        x=forecast.index, y=forecast, mode='lines', name='Vorhersage', line=dict(color='red')))
    fig.update_layout(
        title='Zeitreihen-Vorhersage mit ARIMA',
        xaxis_title='Zeit',
        yaxis_title='Sensorwert'
    )

    return fig