import pandas as pd
import plotly.express as px

def plot_depth_profile(df: pd.DataFrame, float_id: str, variable: str = "temp_c"):
    """
    Plots a depth profile (depth vs variable) for a specific float.
    """
    if df.empty:
        return px.line(title="No Data Available", template="plotly_dark")
        
    df_filtered = df[df["float_id"].astype(str) == str(float_id)].copy()
    if df_filtered.empty:
        return px.line(title=f"No Data for Float {float_id}", template="plotly_dark")
        
    df_filtered = df_filtered.sort_values(by="depth_m", ascending=True)
    
    # Choose x axis title based on variable
    x_title = "Temperature (°C)" if variable == "temp_c" else "Salinity (PSU)"
    
    fig = px.line(
        df_filtered,
        x=variable,
        y="depth_m",
        title=f"Depth Profile - Float {float_id}",
        template="plotly_dark",
        markers=True
    )
    
    # Invert Y axis so surface is at the top
    fig.update_yaxes(autorange="reversed", title="Depth (m)")
    fig.update_xaxes(title=x_title)
    
    # Add horizontal gridlines
    fig.update_layout(yaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.2)'))
    
    return fig
