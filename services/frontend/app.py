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

from components.sidebar import create_topbar

from pages import sensor_box_list, sensor_data_viz, sensor_box_home, sensor_box_stats
from maindash import app

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div([ 
        html.Button(html.Img(src="/assets/icons/menu.svg", className="icon me-2", alt="Menu"), id="sidebar-toggle", className="sidebar-toggle"), # Button für Ein-/Ausklappen
        create_topbar(), 
        html.Div(id='page-content', className="content"), 
    ], className="container-fluid"),
])

# Callback zur Navigation zwischen den Seiten
@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname):
    logger.info(f"Display page callback triggered for pathname: {pathname}") 

    if pathname == '/sensor_boxes':
        return sensor_box_list.layout
    
    if pathname == '/sensor_stats':
        return sensor_box_stats.layout
    
    if pathname == '/data_viz':
        return sensor_data_viz.layout

    elif pathname == '/': 
         logger.info("Navigating to home page.")
         return sensor_box_home.layout
    else:
        logger.warning(f"Page not found for pathname: {pathname}")
        return html.H1("404 - Seite nicht gefunden")


if __name__ == '__main__':
    logger.info("Starting Dash application (development server)...") 
    app.run(debug=True, host='0.0.0.0', port=8050)