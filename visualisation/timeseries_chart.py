import pandas as pd
import plotly.express as px

def plot_timeseries(df: pd.DataFrame, float_id: str, variable: str = "temp_c"):
    """
    Plots a time series for a specific float.
    """
    if df.empty:
        return px.line(title="No Data Available", template="plotly_dark")
        
    df_filtered = df[df["float_id"].astype(str) == str(float_id)].copy()
    if df_filtered.empty:
        return px.line(title=f"No Data for Float {float_id}", template="plotly_dark")
        
    # Group by date and take mean
    df_grouped = df_filtered.groupby("date")[variable].mean().reset_index()
    df_grouped = df_grouped.sort_values(by="date", ascending=True)
    
    y_title = "Temperature (°C)" if variable == "temp_c" else "Salinity (PSU)"
    title_var = "Temperature" if variable == "temp_c" else "Salinity"
    
    fig = px.line(
        df_grouped,
        x="date",
        y=variable,
        title=f"{title_var} over Time - Float {float_id}",
        template="plotly_dark",
        markers=True
    )
    
    fig.update_xaxes(title="Date", rangeslider_visible=True)
    fig.update_yaxes(title=y_title)
    
    return fig
