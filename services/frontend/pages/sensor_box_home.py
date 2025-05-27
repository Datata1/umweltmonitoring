import dash
from dash import dcc
from dash import html
from maindash import app

layout = html.Div([
    html.H1("Willkommen zur Sensordatenplattform!"),

    html.Img(src="/assets/1Bild.png", style={"width": "40%", "margin-bottom": "20px"}),

    html.P("Dies ist die Startseite der Anwendung."),
    html.P("Wähle oben im Menü eine Kategorie aus."),
    
    dcc.Loading(
        id="loading-plot-data", 
        type="graph", 
        fullscreen=False, 
        children=html.Div(id='plot-container') ,
        className="loading-container" 
    )
])