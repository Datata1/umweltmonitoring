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
    ])
])