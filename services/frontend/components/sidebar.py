# services/frontend/app/components/sidebar.py
from dash import html
from dash import dcc

def create_sidebar():
    return html.Div(
        [
            html.H2("Menu", className="display-4"), 
            # Navigationslinks
            html.Nav(className="nav flex-column", children=[
                dcc.Link(
                    [
                        html.Img(src="/assets/icons/box.svg", className="icon me-2", alt="Sensor Box Icon"), 
                        " Sensor Boxen" 
                    ],
                    href="/sensor_boxes",
                    className="nav-link"
                ),
                dcc.Link(
                    [
                        html.Img(src="/assets/icons/bar-chart-2.svg", className="icon me-2", alt="Statistik Icon"), 
                        " Statistik"
                    ],
                    href="/stats",
                    className="nav-link"
                ),
                 dcc.Link(
                    [
                        html.Img(src="/assets/icons/airplay.svg", className="icon me-2", alt="Daten Visualisierung Icon"), 
                        " Daten Visualisierung"
                    ],
                    href="/data_viz",
                    className="nav-link"
                ),
                # Füge hier weitere Links mit Icons hinzu
            ]),
        ],
        id="sidebar", 
        className="sidebar" 
    )