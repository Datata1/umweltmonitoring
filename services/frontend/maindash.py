# Workaround damit callbacks aus anderen Komponenten in die App geladen werden

import dash

app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=['/assets/style.css'])
server = app.server