# pages/sensor_box_home.py
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from maindash import app # Wichtig für den Callback


services = [
    {
        "name": "Prefect",
        "logo_path": "/assets/logos/prefect-logo-black.png", 
        "url": "http://localhost:3000/prefect" 
    },
    {
        "name": "PostgreSQL Admin",
        "logo_path": "/assets/logos/postgres.png", 
        "url": "http://localhost:3000/db-admin" 
    },
    {
        "name": "Backend API Dokumentation",
        "logo_path": "/assets/logos/fastapi.png", 
        "url": "http://localhost:3000/docs" 
    }
]

layout = html.Div([
    html.Img(src="/assets/logos/sensebox_wort_logo.svg", style={"width": "60%", "maxWidth": "800px", "display": "block", "margin": "0 auto 20px auto"}),
    html.P("Startpunkte für die verschiedenen Dienste der Plattform.", className="page-subtitle"),

    # Dieser Container bleibt hier in der Datei
    html.Div(id='model-status-container', className='status-container'),

    html.Div([
        # Die Schleife generiert die Karten
        html.Div([
            # Markenbild/Logo
            html.Img(src=service["logo_path"], className="service-logo"),
            
            # Name des Dienstes
            html.H3(service["name"]),
            
            # Der klickbare Button
            html.A(
                html.Button("Öffnen", className="service-button"),
                href=service["url"],
                target="_blank" 
            )
        ], className="service-card") 
        for service in services
    ], className="service-container")
], className="page-container")


# --- CALLBACK nur für die Statusmeldung auf dieser Seite ---
@app.callback(
    Output('model-status-container', 'children'),
    Input('model-status-store', 'data')
)
def update_home_page_status_message(status):
    """Aktualisiert die Status-Box basierend auf dem Store-Status."""
    if status == 'ready':
        return html.Div([
            html.I(className="bi bi-check-circle-fill me-2"),
            "Modelle sind bereit. Die Vorhersagen sind jetzt verfügbar."
        ], className="status-message ready")
    else:
        return html.Div([
            html.I(className="bi bi-clock-history me-2"),
            "Modelle werden trainiert. Die Vorhersagen sind in Kürze verfügbar..."
        ], className="status-message not-ready")