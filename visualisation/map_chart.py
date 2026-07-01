import pandas as pd
import plotly.express as px

def plot_float_map(df: pd.DataFrame):
    """
    Plots the ARGO float positions on a map, dynamically centering and zooming
    based on the geographic coordinates and proximity filters.
    """
    if df.empty:
        return px.scatter_geo(title="No Data Available", template="plotly_dark")
        
    # Cap plotting points to 1000 for visualization rendering
    plot_df = df.sample(n=min(1000, len(df))) if len(df) > 1000 else df
    
    # Calculate geographical center
    center_lat = plot_df["latitude"].mean()
    center_lon = plot_df["longitude"].mean()
    
    # Determine zoom level based on spatial search type and spread
    if "distance_km" in plot_df.columns:
        # Distance-sorted coordinate proximity query
        zoom = 5
    elif len(plot_df) > 1:
        lat_range = plot_df["latitude"].max() - plot_df["latitude"].min()
        lon_range = plot_df["longitude"].max() - plot_df["longitude"].min()
        # If clustered (e.g., regional search), zoom in
        if lat_range < 30 and lon_range < 30:
            zoom = 4
        else:
            zoom = 2
    else:
        zoom = 4
        
    # Dynamic marker size
    marker_size = 12 if len(plot_df) < 20 else (10 if len(plot_df) < 100 else 7)
    
    fig = px.scatter_mapbox(
        plot_df,
        lat="latitude",
        lon="longitude",
        color="temp_c" if "temp_c" in plot_df.columns else None,
        color_continuous_scale="RdBu_r",
        hover_data=["float_id", "date", "depth_m", "temp_c", "salinity"] if "float_id" in plot_df.columns else None,
        title="ARGO Float Positions",
        mapbox_style="carto-darkmatter",
        zoom=zoom,
        center={"lat": center_lat, "lon": center_lon}
    )
    
    fig.update_traces(marker=dict(size=marker_size))
    
    fig.update_layout(
        margin={"r":0,"t":40,"l":0,"b":0},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig
