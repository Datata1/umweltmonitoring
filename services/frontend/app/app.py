# services/frontend/app/app.py
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import logging 
import sys 


root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

if not root_logger.handlers:
    root_logger.addHandler(handler)

logger = logging.getLogger(__name__)

from components.sidebar import create_sidebar

from pages import sensor_box_list, sensor_data_viz
from maindash import app

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
    logger.info(f"Display page callback triggered for pathname: {pathname}") 

    if pathname == '/sensor_boxes':
        return sensor_box_list.layout
    
    if pathname == '/data_viz':
        return sensor_data_viz.layout

    elif pathname == '/': 
         logger.info("Navigating to home page.")
         return html.H1("Willkommen im Umweltmonitoring Dashboard!")
    else:
        logger.warning(f"Page not found for pathname: {pathname}")
        return html.H1("404 - Seite nicht gefunden")


# Callback zum Ein-/Ausklappen der Seitenleiste
@app.callback(Output('sidebar', 'className'), 
              Input('sidebar-toggle', 'n_clicks'), 
              State('sidebar', 'className'), 
              prevent_initial_call=True)
def toggle_sidebar(n_clicks, current_sidebar_class):
    logger.info(f"Toggle sidebar callback triggered. n_clicks: {n_clicks}, current_class: {current_sidebar_class}") 

    if n_clicks: 
        if current_sidebar_class == "sidebar":
            return "sidebar collapsed"
        else: 
            return "sidebar"
    return "sidebar" 

if __name__ == '__main__':
    logger.info("Starting Dash application (development server)...") 
    app.run(debug=True)