# services/frontend/app/app.py
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import logging 
import sys 
import requests

# --- Logging Konfiguration ---
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not root_logger.handlers:
    root_logger.addHandler(handler)
logger = logging.getLogger(__name__)

# --- URL Konfiguration ---
BACKEND_READINESS_URL = "http://backend:8000/api/v1/health/readiness"

# --- Importe ---
from components.sidebar import create_topbar
from pages import sensor_box_list, sensor_data_viz, sensor_box_home, sensor_box_stats
from maindash import app

# --- App Layout ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='model-status-store'),
    dcc.Interval(
        id='readiness-check-interval',
        interval=5 * 1000,  # Intervall auf 5 Sekunden zurückgesetzt
        n_intervals=0
    ),
    html.Div([ 
        html.Button(html.Img(src="/assets/icons/menu.svg", className="icon me-2", alt="Menu"), id="sidebar-toggle", className="sidebar-toggle"),
        create_topbar(),
        html.Div(id='page-content', className="content"), 
    ], className="container-fluid"),
])

# --- Callbacks ---

# Callback zur Seiten-Navigation
@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname):
    # ... (Dieser Teil ist OK) ...
    logger.info(f"Display page callback triggered for pathname: {pathname}")
    if pathname == '/sensor_boxes':
        return sensor_box_list.layout
    if pathname == '/sensor_stats':
        try:
            response = requests.get(BACKEND_READINESS_URL, timeout=2)
            if response.status_code == 200 and response.json().get("status") == "ready":
                 return sensor_box_stats.layout
        except requests.exceptions.RequestException:
            pass
        return html.Div([html.H2("Zugang gesperrt"), html.P("Die Modelle sind noch nicht bereit.")], className="page-container")
    if pathname == '/data_viz':
        return sensor_data_viz.layout
    elif pathname == '/':
         return sensor_box_home.layout
    else:
        return html.H1("404 - Seite nicht gefunden")

# Callback, der den Backend-Status abfragt und im Store speichert
@app.callback(
    Output('model-status-store', 'data'),
    [Input('readiness-check-interval', 'n_intervals'),
     Input('url', 'pathname')]  # NEU: Löst auch beim Laden der Seite aus
)
def poll_readiness_status(n, pathname):
    """Fragt den Backend-Status ab und speichert das Ergebnis."""
    try:
        response = requests.get(BACKEND_READINESS_URL, timeout=3)
        response.raise_for_status()  # Löst Fehler bei HTTP-Fehlercodes (z.B. 404, 500) aus
        if response.json().get("status") == "ready":
            logger.info("Readiness-Check: Status ist 'ready'.")
            return 'ready'
    except requests.exceptions.RequestException as e:
        # SEHR WICHTIG: Gib den genauen Fehler in der Konsole aus!
        logger.error(f"Fehler beim Abrufen des Readiness-Status: {e}")
    
    # Wenn etwas schiefgeht, wird 'not ready' zurückgegeben
    return 'not ready'

# Callback, der den Link basierend auf dem Store-Status aktualisiert
@app.callback(
    [Output('link-sensor-stats', 'href'),
     Output('link-sensor-stats', 'className')],
    Input('model-status-store', 'data')
)
def update_nav_link_status(status):
    """Aktualisiert den Navigationslink basierend auf dem Store-Status."""
    if status == 'ready':
        return "/sensor_stats", "nav-link"
    else:
        return "#", "nav-link disabled"

if __name__ == '__main__':
    logger.info("Starting Dash application (development server)...") 
    app.run(debug=True, host='0.0.0.0', port=8050)