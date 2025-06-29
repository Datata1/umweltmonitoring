# components/sidebar.py (angenommen, die Datei heißt so)
from dash import html
from dash import dcc

def create_topbar():
    return html.Div(
        [
            # Profilbild oben
            html.Div(
                html.Img(
                    src="assets/iconk.png",
                    alt="Profilbild",
                    className="topbar-image",
                    style={"borderRadius": "50%"}
                ),
                className="topbar-top"
            ),

            # Navigationslinks
            html.Div(
                children=[
                    dcc.Link(
                        [html.Img(src="/assets/icons/home.svg", className="icon"), "Hauptmenu"],
                        href="/",
                        className="nav-link"
                    ),
                    dcc.Link(
                        [html.Img(src="/assets/icons/box.svg", className="icon"), "Sensor Boxen"],
                        href="/sensor_boxes",
                        className="nav-link"
                    ),
                    # --- MODIFIZIERTER LINK ---
                    dcc.Link(
                        [html.Img(src="/assets/icons/bar-chart.svg", className="icon"), "Vorhersagen"],
                        href="#",  # Startet deaktiviert
                        id="link-sensor-stats", # Eindeutige ID hinzugefügt
                        className="nav-link disabled" # Startet mit der "disabled"-Klasse
                    ),
                    # --- ENDE DER MODIFIKATION ---
                    dcc.Link(
                        [html.Img(src="/assets/icons/airplay.svg", className="icon"), "Daten Visualisierung"],
                        href="#", 
                        id="link-data-viz",
                        className="nav-link disabled"
                    )
                ],
                className="nav-container"
            ),
        ],
        id="topbar",
        className="topbar"
    )