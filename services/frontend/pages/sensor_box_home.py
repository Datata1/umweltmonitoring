import dash
from dash import dcc
from dash import html
from maindash import app

layout = html.Div([
    html.H1("Willkommen zur Sensordatenplattform!", style={"textAlign": "center"}),

    html.Div([    
        html.Img(
            src="/assets/1Bild.png", 
            style={"width": "40%", "marginBottom": "20px", "display": "block", "marginLeft": "auto", "marginRight": "auto"}
        ),
    ]),

    html.P("Dies ist die Startseite der Anwendung.", style={"textAlign": "center"}),
    html.P("Wähle oben im Menü eine Kategorie aus.", style={"textAlign": "center"}),

    dcc.Loading(
        id="loading-plot-data", 
        type="graph", 
        fullscreen=False, 
        children=html.Div(id='plot-container'),
        className="loading-container"
    )
])
