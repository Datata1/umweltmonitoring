# services/frontend/app/components/plot.py

from dash import html
from dash import dcc
import plotly.graph_objects as go


def create_time_series_graph(
    id: str,
    title: str,
    data: list, 
    x_col: str, 
    y_col: str,
    y_axis_label: str = "Wert",
    **kwargs 
):
    """
    Erstellt eine wiederverwendbare Komponente zur Anzeige eines Zeitreihen-Graphen.
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
    )

    return html.Div(
        [
            dcc.Graph(
                id=f'{id}-graph', 
                figure=fig,
            )
        ],
        id=id, 
        **kwargs 
    )

def create_heatmap():
    pass

def create_whiskers():
    pass