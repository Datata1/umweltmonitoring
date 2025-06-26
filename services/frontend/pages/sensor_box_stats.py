# services/frontend/app/pages/predictions_dashboard.py (Beispiel-Dateiname)

import os
import sys
import logging
from datetime import datetime, timedelta # timedelta importiert
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

logger = logging.getLogger(__name__)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import dcc, html
from dash.dependencies import Input, Output

from maindash import app
# Annahme, dass api_client korrekt konfiguriert ist
from utils import api_client

# --- Neues, dashboard-orientiertes Layout ---
layout = html.Div(className="dashboard-grid-container", children=[
    
    html.H1("Temperatur-Vorhersage", className="dashboard-title"),
    
    # --- HAUPTBEREICH (LINKS) ---
    html.Div(className="main-plot-area", children=[
        # Container für den Haupt-Plot
        dcc.Loading(
            dcc.Graph(id='prediction-plot', style={'height': '100%'}),
            type="graph"
        ),
        # Container für die KPI-Karten
        html.Div(id='kpi-container', className="kpi-container")
    ]),
    
    # --- INFO-PANEL (RECHTS) ---
    html.Div(className="info-panel", children=[
        html.H4("System-Status"),
        html.Div(id='status-info-container'),
        
        html.H4("Modell-Genauigkeit (RMSE)"),
        dcc.Loading(
            dcc.Graph(id='rmse-plot', style={'height': '300px'}),
            type="graph"
        )
    ]),

    # Komponente zur regelmäßigen Aktualisierung
    dcc.Interval(
        id='interval-component',
        interval=5*60*1000, # Alle 5 Minuten
        n_intervals=0
    )
])


# --- DER NEUE, ZENTRALE CALLBACK FÜR DAS GESAMTE DASHBOARD ---
@app.callback(
    Output('prediction-plot', 'figure'),
    Output('kpi-container', 'children'),
    Output('rmse-plot', 'figure'),
    Output('status-info-container', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_prediction_dashboard(n_intervals):
    try:
        # 1. Daten von beiden Endpunkten abrufen
        predictions_response = api_client.get_predictions()
        models_response = api_client.get_models()
    except Exception as e:
        logger.error(f"Fehler beim API-Abruf: {e}")
        error_fig = go.Figure().update_layout(title_text="Fehler beim Laden der Daten", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        error_msg = html.P(f"Konnte keine Verbindung zum Backend herstellen: {e}", style={'color': 'red'})
        return error_fig, [], error_fig, error_msg

    # --- 2. Daten verarbeiten und Standardwerte initialisieren ---
    plot_data_df = pd.DataFrame(predictions_response.get('plot_data', []))
    models_df = pd.DataFrame(models_response)

    # Standardwerte für den Fall, dass Daten fehlen
    fig_main = go.Figure().update_layout(title_text="Keine Zeitreihendaten verfügbar")
    kpi_cards = [html.P("Keine KPI-Daten verfügbar.")]
    fig_rmse = go.Figure().update_layout(title_text="Keine Modelldaten verfügbar")
    status_info = []

    # --- 3. Haupt-Plot und KPIs erstellen, WENN Daten vorhanden sind ---
    if not plot_data_df.empty and 'timestamp' in plot_data_df.columns:
        # Wandle 'timestamp' sicher um. Fehlerhafte Werte werden zu NaT (Not a Time).
        plot_data_df['timestamp'] = pd.to_datetime(plot_data_df['timestamp'], errors='coerce')
        
        # Entferne Zeilen, bei denen die Datumsumwandlung fehlgeschlagen ist.
        plot_data_df.dropna(subset=['timestamp'], inplace=True)

        # Erneute Prüfung: Führe den Code nur aus, wenn nach der Bereinigung noch gültige Daten vorhanden sind.
        if not plot_data_df.empty:
            historical_df = plot_data_df[plot_data_df['type'] == 'historical']
            predicted_df = plot_data_df[plot_data_df['type'] == 'predicted']
            
            # Haupt-Plot
            fig_main = go.Figure()
            fig_main.add_trace(go.Scatter(
                x=historical_df['timestamp'], y=historical_df['value'],
                mode='lines', name='Historische Temperatur', line=dict(color='#007BFF', width=2)
            ))
            fig_main.add_trace(go.Scatter(
                x=predicted_df['timestamp'], y=predicted_df['value'],
                mode='lines', name='Vorhersage', line=dict(color='#FF5733', width=2, dash='dash')
            ))
            fig_main.update_layout(
                title='Temperaturverlauf und Vorhersage',
                yaxis_title='Temperatur (°C)',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=20, t=50, b=40),
                plot_bgcolor='#ffffff'
            )
            
            # Die "Jetzt"-Linie wird nur hinzugefügt, wenn die Daten erfolgreich verarbeitet wurden.
            now_ts = pd.Timestamp.now(tz=plot_data_df['timestamp'].dt.tz)

            # KORREKTUR: Die Funktion `add_vline` verursacht bei einigen Versionen einen TypeError.
            # Ein robusterer Ansatz ist, die Linie manuell als "shape" und die
            # Beschriftung als "annotation" hinzuzufügen.
            now_dt = now_ts.to_pydatetime()
            fig_main.add_shape(
                type="line",
                x0=now_dt, y0=0, x1=now_dt, y1=1,
                yref="paper", # Die y-Koordinaten sind relativ zur Zeichenfläche (0=unten, 1=oben)
                line=dict(color="black", width=1, dash="dot"),
            )
            fig_main.add_annotation(
                x=now_dt, y=1.05, yref="paper",
                text="Jetzt", showarrow=False,
                font=dict(color="black")
            )
        
            # KPIs
            current_temp = historical_df['value'].iloc[-1] if not historical_df.empty else 'N/A'
            
            three_hours_later = now_ts + timedelta(hours=3)
            twelve_hours_later = now_ts + timedelta(hours=12)

            pred_3h_series = predicted_df[predicted_df['timestamp'] >= three_hours_later]
            pred_12h_series = predicted_df[predicted_df['timestamp'] >= twelve_hours_later]

            pred_3h = pred_3h_series['value'].iloc[0] if not pred_3h_series.empty else 'N/A'
            pred_12h = pred_12h_series['value'].iloc[0] if not pred_12h_series.empty else 'N/A'
            
            kpi_cards = [
                html.Div([html.P("Aktuell", className="kpi-title"), html.P(f"{current_temp:.1f}°C" if isinstance(current_temp, float) else current_temp, className="kpi-value")], className="kpi-card"),
                html.Div([html.P("in 3 Std.", className="kpi-title"), html.P(f"{pred_3h:.1f}°C" if isinstance(pred_3h, float) else pred_3h, className="kpi-value")], className="kpi-card"),
                html.Div([html.P("in 12 Std.", className="kpi-title"), html.P(f"{pred_12h:.1f}°C" if isinstance(pred_12h, float) else pred_12h, className="kpi-value")], className="kpi-card"),
            ]

    # --- 4. RMSE-Plot erstellen, WENN Modelldaten vorhanden sind ---
    if not models_df.empty:
        try:
            fig_rmse = px.bar(
                models_df, 
                x='forecast_horizon_hours', 
                y='val_rmse',
                title='Vorhersagefehler pro Stunde',
                labels={'forecast_horizon_hours': 'Vorhersage-Horizont (Stunden)', 'val_rmse': 'RMSE (°C)'}
            )
            fig_rmse.update_layout(margin=dict(l=20, r=20, t=40, b=20), plot_bgcolor='#f8f9fa')
        except Exception as e:
            logger.warning(f"Konnte RMSE-Plot nicht erstellen: {e}")
            fig_rmse.update_layout(title_text="Fehler bei RMSE-Plot Erstellung")

    # --- 5. Status-Infos erstellen ---
    try:
        last_pred_update = pd.to_datetime(predictions_response['last_updated']).strftime('%d.%m.%Y %H:%M:%S')
        status_info.append(html.P([html.Strong("Letzte Vorhersage: "), last_pred_update]))
    except (KeyError, TypeError, ValueError):
        status_info.append(html.P([html.Strong("Letzte Vorhersage: "), "Nicht verfügbar"]))
    
    try:
        if not models_df.empty and 'last_trained_at' in models_df.columns:
            models_df['last_trained_at'] = pd.to_datetime(models_df['last_trained_at'], errors='coerce')
            models_df.dropna(subset=['last_trained_at'], inplace=True)
            if not models_df.empty:
                max_trained_at = models_df['last_trained_at'].max()
                last_model_train = max_trained_at.strftime('%d.%m.%Y %H:%M:%S')
                status_info.append(html.P([html.Strong("Modelle trainiert am: "), last_model_train]))
            else:
                 status_info.append(html.P([html.Strong("Modelle trainiert am: "), "Nicht verfügbar"]))
        else:
            status_info.append(html.P([html.Strong("Modelle trainiert am: "), "Nicht verfügbar"]))
    except (KeyError, TypeError, ValueError) as e:
        logger.warning(f"Konnte Trainings-Status nicht verarbeiten: {e}")
        status_info.append(html.P([html.Strong("Modelle trainiert am: "), "Nicht verfügbar"]))


    return fig_main, kpi_cards, fig_rmse, status_info
