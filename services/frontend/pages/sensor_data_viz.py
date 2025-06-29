import os
import sys
import logging
import re
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import urllib.parse
import json

logger = logging.getLogger(__name__)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, ALL

import dash_bootstrap_components as dbc


from maindash import app
from utils import api_client

BOX_ID = "5faeb5589b2df8001b980304"

# Sensor-Optionen beim Start der App laden
try:
    sensors = api_client.get_sensors_for_box(BOX_ID)
    sensor_options = [
        {"label": s.get("title", "Sensor"), "value": s["sensor_id"]}
        for s in sensors
    ]
    default_sensor = next(
        (s for s in sensor_options if s["label"].lower() == "temperatur"),
        sensor_options[0] if sensor_options else None,
    )

    DEFAULT_SENSOR_VALUE = default_sensor["value"] if default_sensor else None
except Exception as e:
    logger.error("Fehler beim Abrufen der Sensoren: %s", e)
    sensor_options = []
    DEFAULT_SENSOR_VALUE = None

# ---------------------------------------------------------------
# Konstanten und Standardwerte
# ---------------------------------------------------------------
DEFAULT_START_DATE = (datetime.now() - timedelta(days=7)).date().isoformat()
DEFAULT_END_DATE = datetime.now().date().isoformat()
DEFAULT_INTERVAL_VALUE = "1h" # Geändert für sinnvollere Detail-Plots
DEFAULT_SMOOTHING = 1
DEFAULT_TRENDLINE = 'off'
DEFAULT_ANOMALY = 'off'
DEFAULT_AWINDOW = 20
DEFAULT_TAB = 'tab-timeseries'

INTERVAL_PATTERN = re.compile(r"^\s*\d+\s*[smhdw]\s*$", re.IGNORECASE)

# --- Dashboard-Layout ---
layout = html.Div(
    [
        dcc.Store(id='filter-store'), 
        dcc.Download(id="download-csv"),
        html.Div(
            className="dashboard-container",
            style={'display': 'flex', 'flex': '1 1 auto', 'minHeight': 0},
            children=[
                # --- LINKE SEITENLEISTE (SIDEBAR) ---
                html.Div(
                    className="sidebar",
                    style={'display': 'flex', 'flexDirection': 'column'},
                    children=[
                        html.H2("Steuerung"),
                        html.Div(className="control-group", children=[
                            html.Label("Sensor"),
                            dcc.Dropdown(id="sensor-dropdown", options=sensor_options, value=DEFAULT_SENSOR_VALUE, clearable=False),
                        ]),
                        html.Div(className="control-group", children=[
                            html.Label("Zeitraum"),
                            dcc.DatePickerRange(id="date-range-picker", start_date=DEFAULT_START_DATE, end_date=DEFAULT_END_DATE, display_format="DD.MM.YYYY", style={"width": "100%"}),
                        ]),
                        html.Div(className="control-group", children=[
                             html.Div([
                                html.Label("Intervall"),
                                html.I(className="bi bi-info-circle-fill ms-2", id="tooltip-target-interval", style={"cursor": "pointer"}),
                            ], style={'display': 'flex', 'alignItems': 'center'}),
                            dbc.Tooltip(
                                "Zeitliches Raster für die Datenaggregation. '1h' bedeutet ein Datenpunkt pro Stunde. Kürzel: m=Minute, h=Stunde, d=Tag, w=Woche.",
                                target="tooltip-target-interval",
                                placement="right",
                            ),
                            html.Div([
                                html.Button('1m', id={'type': 'interval-preset', 'index': '1m'}, className='preset-button'),
                                html.Button('1H', id={'type': 'interval-preset', 'index': '1h'}, className='preset-button'),
                                html.Button('6H', id={'type': 'interval-preset', 'index': '6h'}, className='preset-button'),
                                html.Button('1T', id={'type': 'interval-preset', 'index': '1d'}, className='preset-button'),
                            ], className='preset-button-group'),
                            dcc.Input(id="interval-input", type="text", value=DEFAULT_INTERVAL_VALUE, debounce=True, placeholder="z.B. 12h", style={"width": "100%"}),
                        ]),
                        html.Div(className="control-group", children=[
                            html.Div([
                                html.Label("Kurvenglättung"),
                                html.I(className="bi bi-info-circle-fill ms-2", id="tooltip-target-smoothing", style={"cursor": "pointer"}),
                            ], style={'display': 'flex', 'alignItems': 'center'}),
                            dbc.Tooltip(
                                "Glättet die Datenlinie über einen gleitenden Durchschnitt. Ein höherer Wert führt zu einer stärkeren Glättung, kann aber kurzfristige Spitzen verbergen.",
                                target="tooltip-target-smoothing",
                                placement="right",
                            ),
                            dcc.Slider(id="smoothing-slider", min=1, max=20, step=1, value=DEFAULT_SMOOTHING, marks={i: str(i) for i in [1, 5, 10, 15, 20]}),
                        ]),
                        html.Div(className="control-group", children=[
                            html.Label("Trendlinie (nur Zeitverlauf)"),
                            dcc.RadioItems(id='trendline-toggle', options=[{'label': 'An', 'value': 'on'}, {'label': 'Aus', 'value': 'off'}], value=DEFAULT_TRENDLINE, className='radio-toggle', labelClassName='radio-toggle-label'),
                        ]),
                        html.Div(className="control-group", children=[
                            html.Div([
                                html.Label("Anomalien (nur Zeitverlauf)"),
                                html.I(className="bi bi-info-circle-fill ms-2", id="tooltip-target-anomaly-toggle", style={"cursor": "pointer"}),
                            ], style={'display': 'flex', 'alignItems': 'center'}),
                            dbc.Tooltip(
                                "Hebt Datenpunkte hervor, die signifikant vom lokalen Durchschnitt abweichen (mehr als 2 Standardabweichungen).",
                                target="tooltip-target-anomaly-toggle",
                                placement="right",
                            ),
                            dcc.RadioItems(id='anomaly-toggle', options=[{'label': 'An', 'value': 'on'}, {'label': 'Aus', 'value': 'off'}], value=DEFAULT_ANOMALY, className='radio-toggle', labelClassName='radio-toggle-label'),
                        ]),
                        html.Div(className="control-group", children=[
                            html.Div([
                                html.Label("Anomalie-Fenster"),
                                html.I(className="bi bi-info-circle-fill ms-2", id="tooltip-target-anomaly-window", style={"cursor": "pointer"}),
                            ], style={'display': 'flex', 'alignItems': 'center'}),
                             dbc.Tooltip(
                                "Größe des Zeitfensters (Anzahl der Datenpunkte) für die Berechnung des lokalen Durchschnitts bei der Anomalieerkennung.",
                                target="tooltip-target-anomaly-window",
                                placement="right",
                            ),
                            dcc.Slider(id='anomaly-window-slider', min=5, max=100, step=5, value=DEFAULT_AWINDOW, marks={i: str(i) for i in range(5, 101, 15)}),
                        ]),
                        html.Div(
                            className="control-group", style={"marginTop": "auto"},
                            children=[html.Button("Daten als CSV exportieren", id="export-button", n_clicks=0, style={"width": "100%", "padding": "10px"}, className="download-button")]
                        ),
                    ],
                ),
                # --- RECHTER HAUPTBEREICH ---
                html.Div(
                    className="main-content",
                    style={'display': 'flex', 'flexDirection': 'column', 'height': '100%'},
                    children=[
                        dcc.Tabs(
                            id='view-tabs', value=DEFAULT_TAB, style={'flexShrink': 0}, 
                            children=[
                                dcc.Tab(label='Zeitverlauf', value='tab-timeseries', selected_style={'borderTop': '3px solid #4CAF50'}),
                                dcc.Tab(label='Muster-Analyse', value='tab-patterns', selected_style={'borderTop': '3px solid #4CAF50'}),
                                dcc.Tab(label='Werte-Verteilung', value='tab-distribution', selected_style={'borderTop': '3px solid #4CAF50'}),
                            ]
                        ),
                        dcc.Loading(
                            id="loading-plot-data", type="graph", style={'flex': '1 1 auto', 'minHeight': 0},
                            children=html.Div(id="tab-content", className="tab-content-container", style={'height': '100%'}),
                             parent_className="loading-parent-container"
                        )
                    ],
                ),
            ],
        )
    ],
    style={'height': '96vh', 'display': 'flex', 'flexDirection': 'column'}
)

# --- Plotting Helper-Funktionen ---

def create_timeseries_plot(df, filters):
    sensor_id, sensor_title = filters.get('sensor'), next((s["label"] for s in sensor_options if s["value"] == filters.get('sensor')), "Sensor")
    unit = filters.get('unit', '')
    fig = go.Figure(go.Scatter(x=df["time_bucket"], y=df["aggregated_value"], mode="lines", name=sensor_title, line=dict(width=2, color="#4CAF50")))
    if filters.get('trendline') == 'on':
        df_cleaned = df.dropna(subset=['time_bucket', 'aggregated_value']); df_cleaned.loc[:, 'time_numeric'] = pd.to_datetime(df_cleaned['time_bucket']).astype(np.int64) // 10**9
        if len(df_cleaned) > 1: slope, intercept = np.polyfit(df_cleaned['time_numeric'], df_cleaned['aggregated_value'], 1); trendline = slope * df_cleaned['time_numeric'] + intercept; fig.add_trace(go.Scatter(x=df_cleaned['time_bucket'], y=trendline, mode='lines', name='Trendlinie', line=dict(color='rgba(255, 0, 0, 0.5)', dash='dash')))
    if filters.get('anomaly') == 'on' and not df.empty:
        aw = filters.get('awindow', 20); rm = df['aggregated_value'].rolling(window=aw, min_periods=1, center=True).mean(); rs = df['aggregated_value'].rolling(window=aw, min_periods=1, center=True).std()
        anomalies = df[np.abs(df['aggregated_value'] - rm) > (2 * rs)];
        if not anomalies.empty: fig.add_trace(go.Scatter(x=anomalies['time_bucket'], y=anomalies['aggregated_value'], mode='markers', name='Anomalien', marker=dict(color='red', size=10, symbol='circle-open', line=dict(width=2))))
    fig.update_layout(title=f"Verlauf für: <b>{sensor_title}</b>", xaxis_title=None, yaxis_title=f"Wert ({unit})", margin=dict(l=40, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#fdfdff", height=None, showlegend=False)
    max_val, min_val, avg_val = df["aggregated_value"].max(), df["aggregated_value"].min(), df["aggregated_value"].mean(); max_val_prev, min_val_prev, avg_val_prev = filters.get('max_prev'), filters.get('min_prev'), filters.get('avg_prev')
    card_max, card_min, card_avg = create_stat_card("Maximalwert", max_val, max_val_prev, unit), create_stat_card("Minimalwert", min_val, min_val_prev, unit), create_stat_card("Durchschnitt", avg_val, avg_val_prev, unit)
    return html.Div([html.Div(dcc.Graph(figure=fig, style={"height": "100%"}), className="graph-container", style={'flex': '1 1 auto', 'minHeight': 0}), html.Div([card_max, card_min, card_avg], className="stats-container", style={'flex': '0 0 auto', 'padding': '15px 0'})], style={"height": "100%", "width": "100%", "display": "flex", "flexDirection": "column"})

def create_pattern_analysis_plot(df, filters):
    days_in_range = (pd.to_datetime(filters.get('end_date')) - pd.to_datetime(filters.get('start_date'))).days
    df['time_bucket_dt'] = pd.to_datetime(df['time_bucket'])
    if days_in_range <= 14:
        group_by, title_group, x_axis_title = 'hour', "pro Stunde", "Stunde des Tages"
        df[group_by] = df['time_bucket_dt'].dt.hour
    elif days_in_range <= 90:
        group_by, title_group, x_axis_title = 'dayofweek', "pro Wochentag", "Wochentag"
        df[group_by] = df['time_bucket_dt'].dt.dayofweek
        day_map = {0: 'Mo', 1: 'Di', 2: 'Mi', 3: 'Do', 4: 'Fr', 5: 'Sa', 6: 'So'}; df[group_by] = df[group_by].map(day_map)
    else:
        group_by, title_group, x_axis_title = 'month', "pro Monat", "Monat"
        df[group_by] = df['time_bucket_dt'].dt.month
        month_map = {i: datetime(2000, i, 1).strftime('%b') for i in range(1, 13)}; df[group_by] = df[group_by].map(month_map)
    sensor_title, unit = next((s["label"] for s in sensor_options if s["value"] == filters.get('sensor')), "Sensor"), filters.get('unit', '')
    fig = go.Figure(data=[go.Box(x=df[group_by], y=df['aggregated_value'], name='Werteverteilung', line=dict(width=2, color="#4CAF50"))])
    fig.update_layout(title=f"Werteverteilung <b>{title_group}</b> für: <b>{sensor_title}</b>", xaxis_title=x_axis_title, yaxis_title=f"Wert ({unit})", boxmode='group', margin=dict(l=40, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#fdfdff")
    median_by_group = df.groupby(group_by)['aggregated_value'].median()
    highest_median_group, lowest_median_group = median_by_group.idxmax(), median_by_group.idxmin()
    # KORREKTUR: Verwende die Klasse 'stats-container' für einheitliches Layout
    kpi_cards = html.Div([
        create_info_card(f"Gruppe mit höchstem Median", f"{highest_median_group} ({median_by_group.max():.2f} {unit})"),
        create_info_card(f"Gruppe mit niedrigstem Median", f"{lowest_median_group} ({median_by_group.min():.2f} {unit})"),
    ], className="stats-container")
    # KORREKTUR: Reihenfolge geändert (Graph oben, KPIs unten) und Flex-Styling angewendet
    return html.Div([html.Div(dcc.Graph(figure=fig, style={"height": "100%"}), className="graph-container", style={'flex': '1 1 auto', 'minHeight': 0}), html.Div(kpi_cards, style={'flex': '0 0 auto', 'padding': '15px 0'})], style={"display": "flex", "flexDirection": "column", "height": "100%"})

def create_distribution_plot(df, filters):
    sensor_title, unit = next((s["label"] for s in sensor_options if s["value"] == filters.get('sensor')), "Sensor"), filters.get('unit', '')
    mean_val, median_val, std_val, skew_val = df['aggregated_value'].mean(), df['aggregated_value'].median(), df['aggregated_value'].std(), df['aggregated_value'].skew()
    fig = go.Figure(data=[go.Histogram(x=df['aggregated_value'], name='Werteverteilung', nbinsx=30, marker_color="#4CAF50")])
    fig.add_vline(x=mean_val, line_width=2, line_dash="dash", line_color="red", annotation_text="Mittelwert", annotation_position="top left")
    fig.add_vline(x=median_val, line_width=2, line_dash="dot", line_color="green", annotation_text="Median", annotation_position="top right")
    fig.update_layout(title=f"Verteilung der Messwerte für: <b>{sensor_title}</b>", xaxis_title=f"Wert ({unit})", yaxis_title="Anzahl", margin=dict(l=40, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#fdfdff")
    # KORREKTUR: Verwende die Klasse 'stats-container' für einheitliches Layout
    kpi_cards = html.Div([
        create_info_card("Median", f"{median_val:.2f} {unit}"),
        create_info_card("Standardabweichung", f"{std_val:.2f} {unit}"),
        create_info_card("Schiefe", f"{skew_val:.2f}"),
    ], className="stats-container")
    # KORREKTUR: Reihenfolge geändert (Graph oben, KPIs unten) und Flex-Styling angewendet
    return html.Div([html.Div(dcc.Graph(figure=fig, style={"height": "100%"}), className="graph-container", style={'flex': '1 1 auto', 'minHeight': 0}), html.Div(kpi_cards, style={'flex': '0 0 auto', 'padding': '15px 0'})], style={"display": "flex", "flexDirection": "column", "height": "100%"})

def create_stat_card(title, current_value, previous_value, unit):
    trend_icon, previous_text, previous_text_style = None, "", {};
    if all(v is not None and pd.notna(v) for v in [current_value, previous_value]):
        icon_src = None;
        if current_value > previous_value: icon_src, previous_text_style = app.get_asset_url("icons/trending-up.svg"), {"color": "green"}
        elif current_value < previous_value: icon_src, previous_text_style = app.get_asset_url("icons/trending-down.svg"), {"color": "red"}
        if icon_src: trend_icon = html.Img(src=icon_src, className="trend-icon")
        previous_text = f"ggü. {previous_value:.1f} {unit}"
    return html.Div([html.Div([html.P(title, className="stat-title"), trend_icon], className="stat-title-container-flex"), html.P(f"{current_value:.2f} {unit}", className="stat-value"), html.P(previous_text, className="stat-previous", style=previous_text_style)], className="stat-card")

def create_info_card(title, value):
    # KORREKTUR: Nutzt jetzt dieselben Klassen wie create_stat_card für einheitliches Styling
    return html.Div([
        html.Div([html.P(title, className="stat-title")], className="stat-title-container-flex"),
        html.P(value, className="stat-value"),
    ], className="stat-card")

# --- Callbacks für State-Management und URL-Synchronisation ---
@app.callback(Output('filter-store', 'data'), Input('url', 'href'))
def update_store_from_url(href):
    if not href: raise dash.exceptions.PreventUpdate
    parsed_url = urllib.parse.urlparse(href)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    filters = {
        'sensor': query_params.get('sensor', [DEFAULT_SENSOR_VALUE])[0],
        'start_date': query_params.get('start_date', [DEFAULT_START_DATE])[0],
        'end_date': query_params.get('end_date', [DEFAULT_END_DATE])[0],
        'interval': query_params.get('interval', [DEFAULT_INTERVAL_VALUE])[0],
        'smoothing': int(query_params.get('smoothing', [DEFAULT_SMOOTHING])[0]),
        'trendline': query_params.get('trendline', [DEFAULT_TRENDLINE])[0],
        'anomaly': query_params.get('anomaly', [DEFAULT_ANOMALY])[0],
        'awindow': int(query_params.get('awindow', [DEFAULT_AWINDOW])[0]),
        'tab': query_params.get('tab', [DEFAULT_TAB])[0],
    }
    return filters

@app.callback(
    Output('filter-store', 'data', allow_duplicate=True),
    [Input('sensor-dropdown', 'value'), Input('date-range-picker', 'start_date'), Input('date-range-picker', 'end_date'), Input('interval-input', 'value'), Input('smoothing-slider', 'value'), Input('trendline-toggle', 'value'), Input('anomaly-toggle', 'value'), Input('anomaly-window-slider', 'value'), Input('view-tabs', 'value')],
    State('filter-store', 'data'),
    prevent_initial_call=True
)
def update_store_from_ui(sensor, start, end, interval, smoothing, trend, anomaly, awindow, tab, current_filters):
    if not all([sensor, start, end, interval, smoothing, trend, anomaly, awindow, tab]): raise dash.exceptions.PreventUpdate
    new_filters = current_filters.copy() if current_filters else {}
    new_filters.update({'sensor': sensor, 'start_date': start, 'end_date': end, 'interval': interval, 'smoothing': smoothing, 'trendline': trend, 'anomaly': anomaly, 'awindow': awindow, 'tab': tab})
    return new_filters

@app.callback(
    Output('filter-store', 'data', allow_duplicate=True),
    Input({'type': 'interval-preset', 'index': ALL}, 'n_clicks'),
    State('filter-store', 'data'),
    prevent_initial_call=True
)
def update_store_from_preset(n_clicks, current_filters):
    ctx = dash.callback_context
    if not ctx.triggered_id or not any(n_clicks): raise dash.exceptions.PreventUpdate
    button_id, new_interval = ctx.triggered_id, ctx.triggered_id['index']
    if current_filters is None: current_filters = {}
    current_filters['interval'] = new_interval
    return current_filters

@app.callback(
    [Output('sensor-dropdown', 'value'), Output('date-range-picker', 'start_date'), Output('date-range-picker', 'end_date'), Output('interval-input', 'value'), Output('smoothing-slider', 'value'), Output('trendline-toggle', 'value'), Output('anomaly-toggle', 'value'), Output('anomaly-window-slider', 'value'), Output('view-tabs', 'value'), Output('url', 'search')],
    Input('filter-store', 'data')
)
def update_ui_and_url_from_store(filters):
    if filters is None: raise dash.exceptions.PreventUpdate
    search_string = f"?{urllib.parse.urlencode(filters)}"
    return (filters['sensor'], filters['start_date'], filters['end_date'], filters['interval'], filters['smoothing'], filters['trendline'], filters['anomaly'], filters['awindow'], filters['tab'], search_string)

@app.callback(Output("tab-content", "children"), Input("filter-store", "data"))
def update_main_content(filters):
    if filters is None or not all(k in filters for k in ['sensor', 'start_date', 'end_date', 'interval']): return html.P("Lade Filter...")
    active_tab, sensor_id, start_date_str, end_date_str, interval_value, smoothing_value = (filters.get('tab'), filters.get('sensor'), filters.get('start_date'), filters.get('end_date'), filters.get('interval'), filters.get('smoothing'))
    try:
        current_start_date, current_end_date = datetime.fromisoformat(start_date_str), datetime.fromisoformat(end_date_str)
        duration = current_end_date - current_start_date; previous_end_date = current_start_date - timedelta(seconds=1); previous_start_date = previous_end_date - duration
    except (ValueError, TypeError): return html.P("Ungültiges Datumsformat.")
    aggregation_params = {"interval": interval_value, "aggregation_type": "avg", "smoothing_window": smoothing_value, "interpolation": "linear"}
    try:
        current_response = api_client.get_aggregated_data(sensor_id, current_start_date, current_end_date, aggregation_params)
        if not current_response or not current_response.get("aggregated_data"): return html.Div("Keine Daten für den Zeitraum.")
        df = pd.DataFrame(current_response["aggregated_data"])
        if df.empty: return html.Div("Keine Daten für den Zeitraum.")
        filters['unit'] = current_response.get("unit", "")
        if active_tab == 'tab-timeseries':
            previous_response = api_client.get_aggregated_data(sensor_id, previous_start_date, previous_end_date, aggregation_params)
            if previous_response and previous_response.get("aggregated_data"):
                df_prev = pd.DataFrame(previous_response["aggregated_data"])
                if not df_prev.empty: filters.update({'max_prev': df_prev["aggregated_value"].max(), 'min_prev': df_prev["aggregated_value"].min(), 'avg_prev': df_prev["aggregated_value"].mean()})
            return create_timeseries_plot(df, filters)
        elif active_tab == 'tab-patterns':
            return create_pattern_analysis_plot(df, filters)
        elif active_tab == 'tab-distribution':
            return create_distribution_plot(df, filters)
        return html.P("Tab nicht gefunden.")
    except Exception as e:
        logger.error("Fehler beim Laden der Plot-Daten: %s", e, exc_info=True)
        return html.Div(f"Fehler: {str(e)}", style={"color": "red"})

@app.callback(Output("download-csv", "data"), Input("export-button", "n_clicks"), State("filter-store", "data"), prevent_initial_call=True)
def export_csv(n_clicks, filters):
    if n_clicks == 0 or filters is None: raise dash.exceptions.PreventUpdate
    sensor_id, start_date, end_date, smoothing_value, interval_value = (filters.get('sensor'), filters.get('start_date'), filters.get('end_date'), filters.get('smoothing'), filters.get('interval'))
    if not all([sensor_id, start_date, end_date, interval_value]): return dash.no_update
    if not INTERVAL_PATTERN.match(interval_value): return dash.no_update
    try:
        from_date, to_date = datetime.fromisoformat(start_date), datetime.fromisoformat(end_date)
        aggregation_params = {"interval": interval_value.strip().lower(), "aggregation_type": "avg", "smoothing_window": smoothing_value, "interpolation": "linear"}
        response = api_client.get_aggregated_data(sensor_id, from_date, to_date, aggregation_params)
        if not response or not response.get("aggregated_data"): return dash.no_update
        df = pd.DataFrame(response["aggregated_data"])
        sensor_title = next((s["label"] for s in sensor_options if s["value"] == sensor_id), "Sensor").replace(" ", "_").lower()
        filename = f"export_{sensor_title}_{start_date}_bis_{end_date}.csv"
        return dcc.send_data_frame(df.to_csv, filename=filename, index=False)
    except Exception as e:
        logger.error("Fehler beim CSV-Export: %s", e, exc_info=True)
        return dash.no_update

