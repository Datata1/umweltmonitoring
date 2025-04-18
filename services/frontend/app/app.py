# services/frontend/app/app.py
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import logging # Importiere logging
import sys # Importiere sys

# --- Konfiguriere Logging explizit ---
# Erstelle einen Logger für das root-Level (der oberste Logger, der alle Logs sammelt)
root_logger = logging.getLogger()
# Setze das Logging-Level für den root-Logger (z.B. INFO, DEBUG, WARNING, ERROR, CRITICAL)
# INFO ist ein gutes Level, um informative Meldungen zu sehen. DEBUG ist für detaillierteres Debugging.
root_logger.setLevel(logging.INFO)

# Erstelle einen Handler, der die Log-Nachrichten an die Standardausgabe (Konsole) sendet
handler = logging.StreamHandler(sys.stdout)
# Erstelle einen Formatter, der das Format der Log-Nachrichten bestimmt
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Weise den Formatter dem Handler zu
handler.setFormatter(formatter)

# Füge den Handler zum root-Logger hinzu.
# Die Prüfung 'if not root_logger.handlers:' verhindert, dass bei --reload der Handler mehrfach hinzugefügt wird.
if not root_logger.handlers:
    root_logger.addHandler(handler)

# Initialisiere den Logger für dieses spezifische Modul (app.py)
logger = logging.getLogger(__name__)
# --- Ende der Logging Konfiguration ---


# Importiere die Sidebar Komponente
from components.sidebar import create_sidebar

# Importiere die Seiten (bleibt nach dem App Initialisierung)
from pages import sensor_box_list

# Initialisiere die Dash App *zuerst*
app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=['/assets/style.css'])
server = app.server # Für Gunicorn oder andere WSGI/ASGI Server


# Definiere das Basis-Layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div([ # Gesamtcontainer
        # Toggle Button für die Seitenleiste
        html.Button(html.Img(src="/assets/icons/menu.svg", className="icon me-2", alt="Menu"), id="sidebar-toggle", className="sidebar-toggle"), # Button für Ein-/Ausklappen
        create_sidebar(), # Seitenleiste (Muss eine ID haben: 'sidebar')
        html.Div(id='page-content', className="content"), # Hauptinhaltsbereich
    ], className="container-fluid"),
])


# Callback zur Navigation zwischen den Seiten
@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname):
    # Diese Logik wird erst ausgeführt, wenn ein Callback ausgelöst wird (nach Modul-Initialisierung)
    logger.info(f"Display page callback triggered for pathname: {pathname}") # Füge Logging hier hinzu

    if pathname == '/sensor_boxes':
        return sensor_box_list.layout

    # Füge hier Bedingungen für andere Pfade hinzu
    # elif pathname.startswith('/sensor_boxes/'): # Beispiel für Detailseite
    #     # Hier die Logik für die Detailseite aufrufen
    #     # Stelle sicher, dass die sensor_box_details Seite importiert und das Layout zurückgegeben wird
    #     # from pages import sensor_box_details # Hier importieren, falls nötig
    #     box_id = pathname.split('/')[-1]
    #     logger.info(f"Navigating to Sensor Box details page for ID: {box_id}")
    #     return html.Div(f"Details für Sensorbox: {box_id}") # Platzhalter

    elif pathname == '/': # Standard- oder Index-Seite
         logger.info("Navigating to home page.")
         return html.H1("Willkommen im Umweltmonitoring Dashboard!")
    else:
        # Seite nicht gefunden
        logger.warning(f"Page not found for pathname: {pathname}")
        return html.H1("404 - Seite nicht gefunden")


# Callback zum Ein-/Ausklappen der Seitenleiste
@app.callback(Output('sidebar', 'className'), # Ziel: className der Seitenleiste
              Input('sidebar-toggle', 'n_clicks'), # Trigger: Klick auf den Button
              State('sidebar', 'className'), # <-- Füge State hinzu, um den aktuellen className zu lesen
              prevent_initial_call=True)
def toggle_sidebar(n_clicks, current_sidebar_class):
    logger.info(f"Toggle sidebar callback triggered. n_clicks: {n_clicks}, current_class: {current_sidebar_class}") # Füge Logging hier hinzu

    if n_clicks: # Prüfe, ob der Button geklickt wurde (nicht None oder 0)
        if current_sidebar_class == "sidebar":
            return "sidebar collapsed"
        else: # Wenn die Klasse "sidebar collapsed" ist oder etwas anderes
            return "sidebar"

    # Dieser Rückgabewert wird nur erreicht, wenn prevent_initial_call=False ist
    # oder wenn n_clicks None ist (was bei prevent_initial_call=True nicht passiert)
    # Im Normalfall sollte dieser Code nicht erreicht werden, wenn der Callback durch n_clicks getriggert wird
    return "sidebar" # Fallback zum Standardzustand


# Führe die App aus (nur für die lokale Entwicklung/Test)
# Verwende app.run_server für die lokale Entwicklung
if __name__ == '__main__':
    logger.info("Starting Dash application (development server)...") # Füge Logging hier hinzu
    # app.run(debug=True) wurde in app.run_server geändert
    app.run(debug=True)