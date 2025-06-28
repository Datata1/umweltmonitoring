# services/frontend/app/pages/predictions_dashboard.py

import os
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

logger = logging.getLogger(__name__)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import dcc, html
from dash.dependencies import Input, Output

from maindash import app
from utils import api_client

layout = html.Div(className="dashboard-grid-container", children=[
    html.H1("Temperatur-Vorhersage", className="dashboard-title"),

    html.Div(className="main-plot-area", children=[
        dcc.Loading(
            dcc.Graph(id='prediction-plot', style={'height': '80%', 'width': '90%'}),
            type="graph"
        ),
        html.Div(id='kpi-container', className="kpi-container")
    ]),

    html.Div(className="info-panel", children=[
        html.H4("System-Status", style={'margin': '1px 0'}),
        html.Div(id='status-info-container'),
        html.H4("Modell-Genauigkeit (RMSE & MAE)"),
        dcc.Loading(
            dcc.Graph(id='rmse-plot', style={'height': '325px', 'width':'400px'}),
            type="graph"
        )
    ]),

    dcc.Interval(
        id='interval-component',
        interval=5 * 60 * 1000,
        n_intervals=0
    )
])


@app.callback(
    Output('prediction-plot', 'figure'),
    Output('kpi-container', 'children'),
    Output('rmse-plot', 'figure'),
    Output('status-info-container', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_prediction_dashboard(n_intervals):
    try:
        predictions_response = api_client.get_predictions()
        models_response = api_client.get_models()
    except Exception as e:
        logger.error(f"Fehler beim API-Abruf: {e}")
        error_fig = go.Figure().update_layout(
            title_text="Fehler beim Laden der Daten",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        error_msg = html.P(f"Konnte keine Verbindung zum Backend herstellen: {e}", style={'color': 'red'})
        return error_fig, [], error_fig, error_msg

    plot_data_df = pd.DataFrame(predictions_response.get('plot_data', []))
    models_df = pd.DataFrame(models_response)

    fig_main = go.Figure().update_layout(title_text="Keine Zeitreihendaten verfügbar")
    kpi_cards = [html.P("Keine KPI-Daten verfügbar.")]
    fig_rmse = go.Figure().update_layout(title_text="Keine Modelldaten verfügbar")
    status_info = []

    if not plot_data_df.empty and 'timestamp' in plot_data_df.columns:
        plot_data_df['timestamp'] = pd.to_datetime(plot_data_df['timestamp'], errors='coerce')
        plot_data_df.dropna(subset=['timestamp'], inplace=True)

        if not plot_data_df.empty:
            historical_df = plot_data_df[plot_data_df['type'] == 'historical']
            predicted_df = plot_data_df[plot_data_df['type'] == 'predicted']

            fig_main = go.Figure()
            fig_main.add_trace(go.Scatter(
                x=historical_df['timestamp'], y=historical_df['value'],
                mode='lines', name='Historische Temperatur', line=dict(color='#4CAF50', width=2)
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

            now_ts = pd.Timestamp.now(tz=plot_data_df['timestamp'].dt.tz)
            now_dt = now_ts.to_pydatetime()
            fig_main.add_shape(
                type="line",
                x0=now_dt, y0=0, x1=now_dt, y1=1,
                yref="paper",
                line=dict(color="black", width=1, dash="dot"),
            )
            fig_main.add_annotation(
                x=now_dt, y=1.05, yref="paper",
                text="Jetzt", showarrow=False,
                font=dict(color="black")
            )

            current_temp = historical_df['value'].iloc[-1] if not historical_df.empty else 'N/A'
            three_hours_later = now_ts + timedelta(hours=3)
            twelve_hours_later = now_ts + timedelta(hours=12)

            pred_3h_series = predicted_df[predicted_df['timestamp'] >= three_hours_later]
            pred_12h_series = predicted_df[predicted_df['timestamp'] >= twelve_hours_later]

            pred_3h = pred_3h_series['value'].iloc[0] if not pred_3h_series.empty else 'N/A'
            pred_12h = pred_12h_series['value'].iloc[0] if not pred_12h_series.empty else 'N/A'

            # RMSE KPI aus Modell 1h
            try:
                rmse_now = models_df[models_df['forecast_horizon_hours'] == 1]['val_rmse'].values[0]
            except Exception:
                rmse_now = 'N/A'

            kpi_cards = [
                html.Div([html.P("Aktuell", className="kpi-title"), html.P(f"{current_temp:.1f}°C" if isinstance(current_temp, float) else current_temp, className="kpi-value")], className="kpi-card"),
                html.Div([html.P("in 3 Std.", className="kpi-title"), html.P(f"{pred_3h:.1f}°C" if isinstance(pred_3h, float) else pred_3h, className="kpi-value")], className="kpi-card"),
                html.Div([html.P("in 12 Std.", className="kpi-title"), html.P(f"{pred_12h:.1f}°C" if isinstance(pred_12h, float) else pred_12h, className="kpi-value")], className="kpi-card"),
                html.Div([html.P("RMSE (1h)", className="kpi-title"), html.P(f"{rmse_now:.2f}°C" if isinstance(rmse_now, float) else rmse_now, className="kpi-value")], className="kpi-card"),
            ]

    if not models_df.empty:
        try:
            if {'forecast_horizon_hours', 'val_rmse', 'val_mae'}.issubset(models_df.columns):
                melted_df = models_df.melt(
                    id_vars='forecast_horizon_hours',
                    value_vars=['val_rmse', 'val_mae'],
                    var_name='Fehlertyp',
                    value_name='Fehlerwert'
                )

                fig_rmse = px.bar(
                    melted_df,
                    x='forecast_horizon_hours',
                    y='Fehlerwert',
                    color='Fehlertyp',
                    barmode='group',
                    title='Vorhersagefehler pro Stunde (RMSE & MAE)',
                    labels={
                        'forecast_horizon_hours': 'Vorhersage-Horizont (Stunden)',
                        'Fehlerwert': 'Fehler (°C)',
                        'Fehlertyp': 'Metrik'
                    }
                )
                fig_rmse.update_layout(margin=dict(l=20, r=20, t=40, b=20), plot_bgcolor='#f8f9fa')

            else:
                fig_rmse = px.bar(
                    models_df,
                    x='forecast_horizon_hours',
                    y='val_rmse',
                    color='val_rmse',
                    color_continuous_scale='RdYlGn_r',
                    title='Vorhersagefehler (RMSE) pro Stunde',
                    labels={
                        'forecast_horizon_hours': 'Vorhersage-Horizont (Stunden)',
                        'val_rmse': 'RMSE (°C)'
                    }
                )
                fig_rmse.update_layout(margin=dict(l=20, r=20, t=40, b=20), plot_bgcolor='#f8f9fa')

        except Exception as e:
            logger.warning(f"Konnte RMSE/MAE-Plot nicht erstellen: {e}")
            fig_rmse.update_layout(title_text="Fehler bei RMSE-Plot Erstellung")

    try:
        last_pred_update = pd.to_datetime(predictions_response['last_updated']).strftime('%d.%m.%Y %H:%M:%S')
        status_info.append(html.P([html.Strong("Letzte Vorhersage: "), last_pred_update],
    style={'margin': '2px 0'}))
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