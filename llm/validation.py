import pandas as pd

def validate_physical_limits(df: pd.DataFrame) -> list[str]:
    """
    Validates physical marine profiling limits on the retrieved dataset to catch sensor anomalies.
    Returns a list of warnings (empty list if dataset matches all rules).
    """
    warnings = []
    if df.empty:
        return warnings

    for idx, row in df.iterrows():
        float_id = row.get("float_id") or row.get("id") or "unknown"
        date_str = str(row.get("date")) if pd.notna(row.get("date")) else "unknown date"
        
        # 1. Coordinate check
        lat = row.get("latitude")
        lng = row.get("longitude")
        if pd.notna(lat) and (lat < -90.0 or lat > 90.0):
            warnings.append(f"Float {float_id} ({date_str}): Invalid latitude {lat:.4f}")
        if pd.notna(lng) and (lng < -180.0 or lng > 180.0):
            warnings.append(f"Float {float_id} ({date_str}): Invalid longitude {lng:.4f}")

        # 2. Temperature range (-2.0C to 40.0C)
        temp = row.get("temp_c")
        if pd.notna(temp):
            if temp < -2.0 or temp > 40.0:
                warnings.append(
                    f"Float {float_id} ({date_str}): Out-of-bounds temperature {temp:.2f}°C "
                    f"(expected -2.0°C to 40.0°C)"
                )

        # 3. Salinity range (2.0 PSU to 45.0 PSU)
        sal = row.get("salinity")
        if pd.notna(sal):
            if sal < 2.0 or sal > 45.0:
                warnings.append(
                    f"Float {float_id} ({date_str}): Out-of-bounds salinity {sal:.2f} PSU "
                    f"(expected 2.0 to 45.0 PSU)"
                )

        # 4. Pressure-depth consistency
        # In seawater, pressure (dbar) is approximately 1.01 * depth (m)
        depth = row.get("depth_m")
        # In our DB, we store depth_m. Wait, does the DB have pressure?
        # No, the columns are: float_id, date, latitude, longitude, depth_m, temp_c, salinity.
        # But in NetCDF source, there is pressure. Since we only store depth_m in PostgreSQL,
        # we can check if depth_m is negative or unrealistically deep (> 6000m)
        if pd.notna(depth):
            if depth < 0.0 or depth > 6000.0:
                warnings.append(
                    f"Float {float_id} ({date_str}): Anomalous depth {depth:.1f}m "
                    f"(expected 0 to 6000m)"
                )
                
    return warnings
