# Workaround damit callbacks aus anderen Komponenten in die App geladen werden

import dash
import dash_bootstrap_components as dbc


app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=['/assets/style.css', dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP])
server = app.server