import pandas as pd
import plotly.express as px

def plot_float_map(df: pd.DataFrame):
    """
    Plots the ARGO float positions on a map for the Indian Ocean.
    """
    if df.empty:
        return px.scatter_geo(title="No Data Available", template="plotly_dark")
        
    plot_df = df.sample(n=min(1000, len(df))) if len(df) > 1000 else df
    
    fig = px.scatter_mapbox(
        plot_df,
        lat="latitude",
        lon="longitude",
        color="temp_c",
        color_continuous_scale="RdBu_r",
        hover_data=["float_id", "date", "depth_m", "temp_c", "salinity"],
        title="ARGO Float Positions — Indian Ocean",
        mapbox_style="carto-darkmatter",
        zoom=2
    )
    fig.update_layout(
        margin={"r":0,"t":40,"l":0,"b":0},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig
