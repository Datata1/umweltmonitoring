# services/frontend/app/components/plot.py

from dash import html
from dash import dcc
import plotly.graph_objects as go


def create_time_series_graph(
    id: str, # Eindeutige ID für die Komponente (für Callbacks)
    title: str,
    data: list, # Die Daten für den Graphen
    x_col: str, # Name der Spalte für die X-Achse (Zeit)
    y_col: str, # Name der Spalte für die Y-Achse (Wert)
    y_axis_label: str = "Wert", # Label für die Y-Achse
    # Füge hier weitere Parameter für Anpassungen hinzu (Farbe, Linienstil etc.)
    **kwargs # Für zusätzliche HTML attributes auf dem Haupt-Div
):
    """
    Erstellt eine wiederverwendbare Komponente zur Anzeige eines Zeitreihen-Graphen.

    Args:
        id: Eindeutige ID für das Haupt-Div der Komponente.
        title: Titel des Graphen.
        data: Eine Liste von Dictionaries mit den Datenpunkten.
        x_col: Der Schlüssel im Daten-Dictionary für die X-Achse (Zeitstempel).
        y_col: Der Schlüssel im Daten-Dictionary für die Y-Achse (Wert).
        y_axis_label: Label für die Y-Achse.
        **kwargs: Zusätzliche HTML Attribute für das Haupt-Div.

    Returns:
        Ein html.Div, das den Graphen enthält.
    """
    fig = go.Figure()

    if data: 
        fig.add_trace(go.Scatter(
            x=[d[x_col] for d in data],
            y=[d[y_col] for d in data], 
            mode='lines', 
            name=y_col 
        ))

    # Konfiguriere das Layout des Graphen
    fig.update_layout(
        title=title,
        xaxis_title="Zeit",
        yaxis_title=y_axis_label,
        hovermode='x unified', 
        # Füge hier weitere Layout-Anpassungen hinzu (Achsenformatierung, Legende etc.)
    )

    # Erstelle die Dash Komponente
    return html.Div(
        [
            dcc.Graph(
                id=f'{id}-graph', 
                figure=fig,
                # Füge hier weitere dcc.Graph Konfigurationen hinzu (config, animate etc.)
            )
        ],
        id=id, 
        **kwargs 
    )

def create_heatmap():
    pass

def create_whiskers():
    pass