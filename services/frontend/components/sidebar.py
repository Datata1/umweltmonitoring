from dash import html
from dash import dcc

def create_topbar():
    return html.Div(
        [
            # Profilbild ganz links
            html.Div(
                html.Img(
                    src="assets/iconk.png",
                    className="topbar-image",
                    alt="Profilbild"
                ),
                className="topbar-left"
            ),

            # Navigationslinks daneben
            html.Div(
                className="nav-container",
                children=[
                    dcc.Link(
                        [html.Img(src="/assets/icons/homeb.svg", className="icon"), "Hauptmenu"],
                        href="/",
                        className="nav-link"
                    ),
                    dcc.Link(
                        [html.Img(src="/assets/icons/box.svg", className="icon"), "Sensor Boxen"],
                        href="/sensor_boxes",
                        className="nav-link"
                    ),
                    dcc.Link(
                        [html.Img(src="/assets/icons/bar-chart-2.svg", className="icon"), "Statistik"],
                        href="/stats",
                        className="nav-link"
                    ),
                    dcc.Link(
                        [html.Img(src="/assets/icons/airplay.svg", className="icon"), "Daten Visualisierung"],
                        href="/data_viz",
                        className="nav-link"
                    ),
                ]
            ),
        ],
        id="topbar"
    )
