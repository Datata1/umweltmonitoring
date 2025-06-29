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

    # Container für den Modell-Status (bereits vorhanden)
    html.Div([
        # Container für den Modell-Status
        html.Div(id='model-status-container'),

        # Container für den Daten-Ingestion-Status
        html.Div(id='data-ingestion-status-container'),

    ], className="status-group-container"),

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


# --- Callback für den Modell-Status (unverändert) ---
@app.callback(
    Output('model-status-container', 'children'),
    Input('model-status-store', 'data')
)
def update_home_page_model_status_message(status):
    """Aktualisiert die Status-Box für die Modelle."""
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


# --- NEU: Callback für den Daten-Ingestion-Status ---
@app.callback(
    Output('data-ingestion-status-container', 'children'),
    Input('data-viz-status-store', 'data')
)
def update_home_page_data_status_message(status):
    """Aktualisiert die Status-Box für die Datenvisualisierung."""
    # Zeige die Box nur an, wenn der Status bekannt ist (also nicht None)
    if status is None:
        return None

    if status == 'ready':
        return html.Div([
            html.I(className="bi bi-check-circle-fill me-2"),
            "Daten sind verarbeitet. Die Visualisierung ist jetzt verfügbar."
        ], className="status-message ready")
    else:
        return html.Div([
            html.I(className="bi bi-clock-history me-2"),
            "Daten werden noch verarbeitet. Die Visualisierung ist in Kürze verfügbar..."
        ], className="status-message not-ready")