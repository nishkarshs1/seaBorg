import os
import pandas as pd
import plotly.graph_objects as go

def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def export_csv(df: pd.DataFrame, path: str = "data/exports/results.csv") -> str:
    """Saves DataFrame as CSV."""
    _ensure_dir(path)
    df.to_csv(path, index=False)
    return path

def export_chart_html(fig: go.Figure, path: str = "data/exports/chart.html") -> str:
    """Saves Plotly figure as interactive HTML."""
    _ensure_dir(path)
    fig.write_html(path)
    return path

def export_chart_png(fig: go.Figure, path: str = "data/exports/chart.png") -> str:
    """Saves Plotly figure as static PNG image."""
    _ensure_dir(path)
    fig.write_image(path)
    return path
