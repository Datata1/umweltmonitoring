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
                    dcc.Link(
                        [html.Img(src="/assets/icons/bar-chart.svg", className="icon"), "Vorhersagen"],
                        href="/sensor_stats",
                        className="nav-link"
                    ),
                    dcc.Link(
                        [html.Img(src="/assets/icons/airplay.svg", className="icon"), "Daten Visualisierung"],
                        href="/data_viz",
                        className="nav-link"
                    ),
                ],
                className="nav-container"
            ),
        ],
        id="topbar",
        className="topbar"
    )
