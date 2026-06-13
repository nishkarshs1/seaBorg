import pandas as pd
import plotly.express as px

def plot_float_map(df: pd.DataFrame):
    """
    Plots the ARGO float positions on a map for the Indian Ocean.
    """
    if df.empty:
        return px.scatter_geo(title="No Data Available", template="plotly_dark")
        
    fig = px.scatter_geo(
        df,
        lat="latitude",
        lon="longitude",
        color="temp_c",
        color_continuous_scale="RdBu_r",
        hover_data=["float_id", "date", "depth_m", "temp_c", "salinity"],
        title="ARGO Float Positions — Indian Ocean",
        template="plotly_dark"
    )
    fig.update_geos(
        showocean=True, oceancolor="lightblue",
        showland=True, landcolor="darkgray",
        showcoastlines=True, coastlinecolor="white",
        showframe=False
    )
    return fig
