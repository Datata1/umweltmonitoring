import dash
from dash import dcc
from dash import html
from maindash import app

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
    # Haupt-Überschrift und Logo
    html.Img(src="/assets/logos/sensebox_wort_logo.svg", style={"width": "60%", "maxWidth": "800px", "display": "block", "margin": "0 auto 20px auto"}),
    html.P("Startpunkte für die verschiedenen Dienste der Plattform.", className="page-subtitle"),

    # Der Container für die Service-Karten
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
