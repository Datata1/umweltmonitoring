import os
import sys
import logging
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# --- Grundkonfiguration ---
logger = logging.getLogger(__name__)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

from maindash import app
from utils import api_client

# =============================================================================
# HELPER-FUNKTIONEN (unverändert)
# =============================================================================
def create_prediction_plot_layout(predictions_data):
    """Erstellt den Haupt-Vorhersageplot für eine einzelne Vorhersagelinie."""
    if not predictions_data or 'plot_data' not in predictions_data:
        return html.Div("Keine Vorhersagedaten verfügbar.", className="p-4")

    plot_data_df = pd.DataFrame(predictions_data.get('plot_data', []))
    if plot_data_df.empty:
        return html.Div("Keine Zeitreihendaten für den Plot vorhanden.", className="p-4")

    # Datenvorverarbeitung (unverändert)
    plot_data_df['timestamp'] = pd.to_datetime(plot_data_df['timestamp'], errors='coerce')
    plot_data_df.dropna(subset=['timestamp'], inplace=True)
    historical_df = plot_data_df[plot_data_df['type'] == 'historical']
    predicted_df = plot_data_df[plot_data_df['type'] == 'predicted']

    # Plot-Erstellung (unverändert)
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
        title='Temperaturverlauf und Vorhersage', yaxis_title='Temperatur (°C)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=50, b=20), plot_bgcolor='#ffffff', paper_bgcolor="rgba(0,0,0,0)", height=None
    )
    now_ts_utc = pd.Timestamp.now(tz='UTC')
    fig_main.add_shape(type="line", x0=now_ts_utc, y0=0, x1=now_ts_utc, y1=1, yref="paper", line=dict(color="black", width=1, dash="dot"))
    fig_main.add_annotation(x=now_ts_utc, y=1.05, yref="paper", text="Jetzt", showarrow=False, font=dict(color="black"))

    # ✨✨✨ HIER IST DIE ÄNDERUNG: Aussagekräftigere KPIs berechnen ✨✨✨
    
    # Aktuelle Temperatur (bleibt gleich)
    current_temp = historical_df['value'].iloc[-1] if not historical_df.empty else 'N/A'
    
    # Zukünftige Vorhersagen filtern
    future_predictions = predicted_df[predicted_df['timestamp'] > now_ts_utc]

    # KPIs für Min/Max initialisieren
    max_pred_val, max_pred_time_str = 'N/A', ''
    min_pred_val, min_pred_time_str = 'N/A', ''

    if not future_predictions.empty:
        # Maximalwert finden
        max_pred_row = future_predictions.loc[future_predictions['value'].idxmax()]
        max_pred_val = max_pred_row['value']
        max_pred_time_str = f"um {pd.to_datetime(max_pred_row['timestamp']).strftime('%H:%M')} Uhr"

        # Minimalwert finden
        min_pred_row = future_predictions.loc[future_predictions['value'].idxmin()]
        min_pred_val = min_pred_row['value']
        min_pred_time_str = f"um {pd.to_datetime(min_pred_row['timestamp']).strftime('%H:%M')} Uhr"

    # Neue KPI-Karten erstellen
    kpi_cards = [
        # Karte 1: Aktueller Messwert
        dbc.Card([
            dbc.CardBody([
                html.P("Aktuell (gemessen)", className="stat-title mb-2"),
                html.H4(f"{current_temp:.1f}°C" if isinstance(current_temp, (int, float)) else current_temp, className="stat-value"),
            ])
        ], className="stat-card"),

        # Karte 2: Prognostiziertes Maximum
        dbc.Card([
            dbc.CardBody([
                html.P("Progn. Maximum", className="stat-title mb-2"),
                html.H4(f"{max_pred_val:.1f}°C" if isinstance(max_pred_val, (int, float)) else max_pred_val, className="stat-value text-danger"),
                html.P(max_pred_time_str, className="stat-time text-muted"),
            ])
        ], className="stat-card"),

        # Karte 3: Prognostiziertes Minimum
        dbc.Card([
            dbc.CardBody([
                html.P("Progn. Minimum", className="stat-title mb-2"),
                html.H4(f"{min_pred_val:.1f}°C" if isinstance(min_pred_val, (int, float)) else min_pred_val, className="stat-value text-info"),
                html.P(min_pred_time_str, className="stat-time text-muted"),
            ])
        ], className="stat-card"),
    ]
    
    # Layout zusammensetzen
    return html.Div([
        html.Div(dcc.Graph(figure=fig_main, style={"height": "100%"}), className="graph-container", style={'flex': '1 1 auto', 'minHeight': 0}),
        dbc.CardGroup(kpi_cards, className="stats-container", style={'flex': '0 0 auto', 'padding': '15px 0', 'gap': '15px'}),
    ], style={"height": "100%", "width": "100%", "display": "flex", "flexDirection": "column"})

def create_single_model_view(model_data, historical_pred_data):
    """Erstellt die Detailansicht für ein einzelnes Modell mit Graph und Metriken."""
    if model_data is None or model_data.empty:
        return html.P("Keine Modelldaten verfügbar.")
    model_metrics = model_data.iloc[0].to_dict()
    horizon = model_metrics.get('forecast_horizon_hours', 'N/A')
    fig = go.Figure()
    if historical_pred_data:
        actual_df = pd.DataFrame(historical_pred_data.get('actual_data', []))
        predicted_df = pd.DataFrame(historical_pred_data.get('predicted_data', []))
        naive_df = pd.DataFrame(historical_pred_data.get('naive_data', []))
        if not actual_df.empty:
            actual_df['timestamp'] = pd.to_datetime(actual_df['timestamp'])
            fig.add_trace(go.Scatter(x=actual_df['timestamp'], y=actual_df['value'], name='Tatsächliche Werte', mode='lines', line=dict(color='deepskyblue', width=2.5)))
        if not predicted_df.empty:
            predicted_df['timestamp'] = pd.to_datetime(predicted_df['timestamp'])
            fig.add_trace(go.Scatter(x=predicted_df['timestamp'], y=predicted_df['value'], name='ML-Modell Vorhersage', mode='lines', line=dict(color='red', width=2, dash='dash')))
        if not naive_df.empty:
            naive_df['timestamp'] = pd.to_datetime(naive_df['timestamp'])
            fig.add_trace(go.Scatter(x=naive_df['timestamp'], y=naive_df['value'], name='Naives Modell (24h Shift)', mode='lines', line=dict(color='grey', width=1.5, dash='dot')))
    fig.update_layout(
        title=f'Modell-Performance vs. Realität ({horizon}h Horizont)', yaxis_title='Temperatur (°C)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=50, b=20), plot_bgcolor='#f8f9fa', paper_bgcolor="rgba(0,0,0,0)"
    )
    graph_component = dcc.Graph(figure=fig)

    # --- ✨ HIER BEGINNT DIE ÄNDERUNG FÜR DIE STATS-KARTEN ✨ ---

    def get_comparison_metrics(ml_val, naive_val):
        metrics = {'perc_imp': 'N/A', 'skill_score': 'N/A', 'style': 'text-muted'}
        if not all(isinstance(v, (int, float)) for v in [ml_val, naive_val]): return metrics
        if ml_val < naive_val: metrics['style'] = 'text-success'
        elif ml_val > naive_val: metrics['style'] = 'text-danger'
        if naive_val != 0:
            metrics['perc_imp'] = f"{((naive_val - ml_val) / abs(naive_val)) * 100:+.1f}%"
            metrics['skill_score'] = f"{1 - (ml_val / naive_val):.3f}"
        return metrics

    val_rmse = model_metrics.get('val_rmse', 'N/A')
    naive_val_rmse = model_metrics.get('naive_val_rmse', 'N/A')
    val_r2 = model_metrics.get('val_r2', 'N/A')
    val_mae = model_metrics.get('val_mae', 'N/A')
    naive_val_mae = model_metrics.get('naive_val_mae', 'N/A')

    rmse_comp = get_comparison_metrics(val_rmse, naive_val_rmse)
    mae_comp = get_comparison_metrics(val_mae, naive_val_mae)
    
    # Helfer-Funktion, um eine einzelne Wert-Zeile zu erstellen
    def create_metric_row(label, value, is_ml=False):
        val_str = f"{value:.4f}" if isinstance(value, (int, float)) else "N/A"
        style = rmse_comp['style'] if is_ml else {}
        return html.Div([html.Span(label), html.Span(val_str, className=f"fw-bold {style if label.startswith('ML') else ''}")], className="d-flex justify-content-between")

    # Helfer-Funktion, um eine Vergleichs-Zeile zu erstellen (Verbesserung / Skill Score)
    def create_comparison_row(label, value, style_class, unit=""):
         return html.Div([html.Span(label), html.Span(f"{value}{unit}", className=f"fw-bold {style_class}")], className="d-flex justify-content-between mt-1")


    stats_component = dbc.CardGroup([
        # --- Karte 1: RMSE ---
        dbc.Card([
            dbc.CardHeader("RMSE (Root Mean Square Error)"),
            dbc.CardBody([
                create_metric_row("ML Modell", val_rmse, is_ml=True),
                create_metric_row("Naives Modell", naive_val_rmse),
                html.Hr(className="my-2"),
                create_comparison_row("Verbesserung", rmse_comp['perc_imp'], rmse_comp['style']),
                create_comparison_row("Skill Score", rmse_comp['skill_score'], rmse_comp['style']),
            ])
        ]),
        # --- Karte 2: MAE ---
        dbc.Card([
            dbc.CardHeader("MAE (Mean Absolute Error)"),
            dbc.CardBody([
                create_metric_row("ML Modell", val_mae, is_ml=True),
                create_metric_row("Naives Modell", naive_val_mae),
                html.Hr(className="my-2"),
                create_comparison_row("Verbesserung", mae_comp['perc_imp'], mae_comp['style']),
                create_comparison_row("Skill Score", mae_comp['skill_score'], mae_comp['style']),
            ])
        ]),
        # --- Karte 3: R² ---
        dbc.Card([
            dbc.CardHeader("R² Score"),
            dbc.CardBody([
                 html.H4(f"{val_r2:.4f}" if isinstance(val_r2, float) else "N/A", className="card-title text-center my-auto"),
                 html.P("Bestimmungsgütemaß", className="card-text text-muted text-center mt-2")
            ])
        ])
    ], className="stats-container")

    # --- ✨ HIER ENDET DIE ÄNDERUNG FÜR DIE STATS-KARTEN ✨ ---

    return html.Div([graph_component, stats_component], style={"height": "100%", "width": "100%", "display": "flex", "flexDirection": "column"})

def create_performance_layout_with_subtabs(models_data):
    if not models_data: return html.Div("Keine Modelldaten zum Erstellen der Tabs verfügbar.", className="p-4")
    models_df = pd.DataFrame(models_data).sort_values('forecast_horizon_hours')
    models_df = models_df[models_df['forecast_horizon_hours'] <= 24]
    sub_tabs = [dcc.Tab(label=f'{h}h', value=f'subtab-h{h}') for h in models_df['forecast_horizon_hours']]
    
    # ÄNDERUNG: Keinen Standard-Tab auswählen
    default_sub_tab = None 
    
    return html.Div([
        dcc.Tabs(id='pred_performance-sub-tabs', value=default_sub_tab, children=sub_tabs, parent_className='custom-tabs', className='custom-tabs-container'),
        dcc.Loading(html.Div(id='pred_performance-sub-tab-content', style={'height': '100%'}))
    ])

def create_status_info_layout(data):
    if not data or 'predictions' not in data or 'models' not in data: return [html.P("Statusinformationen werden geladen...")]
    predictions_response, models_response = data['predictions'], data['models']
    status_info = []
    try:
        status_info.append(html.P([html.Strong("Letzte Vorhersage: "), pd.to_datetime(predictions_response['last_updated']).strftime('%d.%m.%Y %H:%M:%S')]))
    except (KeyError, TypeError, ValueError):
        status_info.append(html.P([html.Strong("Letzte Vorhersage: "), "Nicht verfügbar"]))
    try:
        models_df = pd.DataFrame(models_response)
        if not models_df.empty and 'last_trained_at' in models_df.columns:
            last_model_train = pd.to_datetime(models_df['last_trained_at']).max().strftime('%d.%m.%Y %H:%M:%S')
            status_info.append(html.P([html.Strong("Modelltraining: "), last_model_train]))
        else: raise ValueError("Trainingsdatum nicht verfügbar.")
    except Exception:
        status_info.append(html.P([html.Strong("Modelltraining: "), "Nicht verfügbar"]))
    return status_info

def create_model_details_layout(model_dict):
    if not model_dict:
        return dbc.Card([
            dbc.CardHeader("Modelldetails"),
            dbc.CardBody(html.P("Wähle ein Modell aus, um Details anzuzeigen.", className="card-text text-muted"))
        ], className="mb-3")

    def create_list_group_item(title, value, unit=""):
        if value is None or pd.isna(value):
            return None
        return dbc.ListGroupItem([
            html.Strong(f"{title}: "), f"{value}{unit}"
        ], className="d-flex justify-content-between align-items-center")

    last_trained = pd.to_datetime(model_dict.get('last_trained_at')).strftime('%d.%m.%Y %H:%M') if model_dict.get('last_trained_at') else 'N/A'
    train_duration = f"{model_dict.get('training_duration_seconds'):.2f}" if model_dict.get('training_duration_seconds') is not None else 'N/A'

    items = [
        create_list_group_item("Version", model_dict.get('version_id')),
        create_list_group_item("Letztes Training", last_trained),
        create_list_group_item("Trainingsdauer", train_duration, " s"),
        create_list_group_item("Validierungs-MAE", f"{model_dict.get('val_mae'):.4f}"),
        create_list_group_item("Validierungs-RMSE", f"{model_dict.get('val_rmse'):.4f}"),
        create_list_group_item("Validierungs-R²", f"{model_dict.get('val_r2'):.4f}"),
    ]

    return dbc.Card([
        dbc.CardHeader(f"Details: {model_dict.get('forecast_horizon_hours')}h Modell"),
        dbc.CardBody(
            dbc.ListGroup([item for item in items if item is not None], flush=True)
        )
    ], className="mb-3")

# =============================================================================
# DASHBOARD LAYOUT (unverändert)
# =============================================================================
layout = html.Div([
    dcc.Store(id='pred_api-data-store'),
    dcc.Interval(id='pred_interval-component', interval=5 * 60 * 1000, n_intervals=0),
    html.Div(className="dashboard-container", style={'display': 'flex', 'flex': '1 1 auto', 'minHeight': 0}, children=[
        html.Div(className="sidebar", style={'display': 'flex', 'flexDirection': 'column'}, children=[
            html.H2("Informationen"),
            html.Div(className="control-group", children=[
                html.Label("System-Status", style={'font-weight': 'bold'}),
                dcc.Loading(id="pred_loading-status-info", type="default", children=html.Div(id='pred_status-info-container', style={'paddingTop': '10px'})),
            ]),
            html.Div(className="control-group mt-3", children=[
                html.Label("Modelldetails", style={'font-weight': 'bold'}),
                dcc.Loading(id="pred_loading-model-details", type="default", children=html.Div(id='pred_model-details-container', style={'paddingTop': '10px'})),
            ]),
        ]),
        html.Div(className="main-content", style={'display': 'flex', 'flexDirection': 'column', 'height': '100%'}, children=[
            dcc.Tabs(id='pred_view-tabs', value='tab-predictions', style={'flexShrink': 0}, children=[
                dcc.Tab(label='Temperatur-Vorhersage', value='tab-predictions', selected_style={'borderTop': '3px solid #4CAF50'}),
                dcc.Tab(label='Modell-Genauigkeit', value='tab-performance', selected_style={'borderTop': '3px solid #4CAF50'}),
            ]),
            dcc.Loading(id="pred_loading-tab-content", type="graph", style={'flex': '1 1 auto', 'minHeight': 0}, children=[
                html.Div(id='pred_tab-content-predictions', className="tab-content-container", style={'height': '100%'}),
                html.Div(id='pred_tab-content-performance', className="tab-content-container", style={'height': '100%'})
            ]),
        ]),
    ])
], style={'height': '96vh', 'display': 'flex', 'flexDirection': 'column'})

# =============================================================================
# CALLBACKS
# =============================================================================
@app.callback(
    Output('pred_api-data-store', 'data'),
    Input('pred_interval-component', 'n_intervals')
)
def fetch_data_from_api(n_intervals):
    try:
        return {'predictions': api_client.get_predictions(), 'models': api_client.get_models(), 'error': None}
    except Exception as e:
        logger.error(f"Fehler beim API-Abruf: {e}")
        return {'predictions': None, 'models': None, 'error': f"Konnte keine Verbindung zum Backend herstellen: {e}"}

@app.callback(
    [Output('pred_tab-content-predictions', 'style'),
     Output('pred_tab-content-performance', 'style')],
    Input('pred_view-tabs', 'value')
)
def switch_main_tab_visibility(active_tab):
    if active_tab == 'tab-predictions':
        return {'display': 'block', 'height': '100%'}, {'display': 'none'}
    elif active_tab == 'tab-performance':
        return {'display': 'none'}, {'display': 'block', 'height': '100%'}
    return {'display': 'block', 'height': '100%'}, {'display': 'none'}

@app.callback(
    Output('pred_tab-content-predictions', 'children'),
    Input('pred_api-data-store', 'data')
)
def populate_predictions_tab(data):
    if data is None: return html.P("Daten werden geladen...")
    if data.get('error'): return html.Div(f"Fehler: {data['error']}", style={"color": "red", "padding": "20px"})
    return create_prediction_plot_layout(data.get('predictions'))

@app.callback(
    Output('pred_tab-content-performance', 'children'),
    Input('pred_api-data-store', 'data')
)
def populate_performance_tab(data):
    if data is None: return html.P("Daten werden geladen...")
    if data.get('error'): return html.Div(f"Fehler: {data['error']}", style={"color": "red", "padding": "20px"})
    return create_performance_layout_with_subtabs(data.get('models'))

@app.callback(
    Output('pred_performance-sub-tab-content', 'children'),
    Input('pred_performance-sub-tabs', 'value'),
    State('pred_api-data-store', 'data')
)
def render_performance_sub_tab(sub_tab_value, data):
    if not sub_tab_value: return html.P("Bitte einen Vorhersage-Horizont auswählen.")
    if data is None or data.get('models') is None: return html.P("Warte auf Modelldaten...")
    models_df = pd.DataFrame(data.get('models', []))
    try:
        horizon = int(sub_tab_value.replace('subtab-h', ''))
        single_model_df = models_df[models_df['forecast_horizon_hours'] == horizon]
        historical_pred_data = api_client.get_historical_predictions_for_model(horizon)
        return create_single_model_view(single_model_df, historical_pred_data)
    except Exception as e:
        logger.error(f"Fehler bei der Verarbeitung für Horizont '{sub_tab_value}': {e}", exc_info=True)
        return html.Div(f"Fehler beim Laden der Daten für {sub_tab_value}: {e}", className="p-4 text-danger")

@app.callback(
    Output('pred_status-info-container', 'children'),
    Input('pred_api-data-store', 'data')
)
def update_status_info(data):
    if data is None: return html.P("Warte auf Daten...")
    if data.get('error'): return html.P("Status nicht verfügbar.", style={"color": "orange"})
    return create_status_info_layout(data)


# ✨✨✨ HIER IST DIE KORREKTUR ✨✨✨
# Ersetzt die beiden vorherigen Callbacks für die Sidebar.
@app.callback(
    Output('pred_model-details-container', 'children'),
    [Input('pred_view-tabs', 'value'),
     Input('pred_performance-sub-tabs', 'value')],
    State('pred_api-data-store', 'data'),
    prevent_initial_call=True
)
def update_model_details_sidebar(active_main_tab, active_sub_tab, data):
    # Fall 1: Wir sind nicht auf dem Performance-Tab -> Details zurücksetzen.
    if active_main_tab != 'tab-performance':
        return create_model_details_layout(None)

    # Fall 2: Wir SIND auf dem Performance-Tab.
    # Zeige Details für den aktuell ausgewählten Sub-Tab an.
    if not active_sub_tab or not data or not data.get('models'):
        return create_model_details_layout(None)

    try:
        horizon = int(active_sub_tab.replace('subtab-h', ''))
        models_df = pd.DataFrame(data['models'])
        model_series = models_df[models_df['forecast_horizon_hours'] == horizon].iloc[0]
        return create_model_details_layout(model_series.to_dict())
    except (IndexError, ValueError) as e:
        # Dieser Fehler kann auftreten, wenn die Daten neu laden und der alte Sub-Tab nicht mehr existiert.
        logger.warning(f"Konnte Modelldetails für Sub-Tab '{active_sub_tab}' nicht finden: {e}")
        return create_model_details_layout(None) # Sicherer Reset