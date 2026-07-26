import io
import pandas as pd
from dotenv import load_dotenv
from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from api.models import ExportRequest, ExportReportRequest, ChatTurn
from rag.retriever import SIMILARITY_THRESHOLD

load_dotenv()

router = APIRouter()


def _get_engine():
    """Returns a SQLAlchemy engine."""
    from db.connection import get_engine
    return get_engine()


def _query_data(req: ExportRequest) -> pd.DataFrame:
    """
    Queries argo_profiles filtered by float_ids and optional date range.

    Args:
        req: ExportRequest with float_ids, format, and optional date filters.

    Returns:
        DataFrame of matching rows.

    Side effects:
        Queries PostgreSQL.
    """
    engine = _get_engine()
    conditions = ["float_id = ANY(:float_ids)"]
    params: dict = {"float_ids": req.float_ids}

    if req.start_date:
        conditions.append("date >= :start_date")
        params["start_date"] = req.start_date
    if req.end_date:
        conditions.append("date <= :end_date")
        params["end_date"] = req.end_date

    where = " AND ".join(conditions)
    sql = f"SELECT * FROM argo_profiles WHERE {where} ORDER BY float_id, date, depth_m"

    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


@router.post("/export")
def export_data(req: ExportRequest):
    """
    Streams a file download of ARGO data in CSV or NetCDF format.

    Args:
        req: ExportRequest specifying float_ids, format, and optional date range.

    Returns:
        StreamingResponse with appropriate Content-Type and Content-Disposition headers.

    Side effects:
        Queries PostgreSQL and streams file bytes to the client.
    """
    df = _query_data(req)

    if req.format == "csv":
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="seaborg_export.csv"'
            },
        )

    if req.format == "netcdf":
        import xarray as xr
        ds = xr.Dataset.from_dataframe(df.set_index(["float_id", "date"]))
        buffer = io.BytesIO()
        ds.to_netcdf(buffer)
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.read()]),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": 'attachment; filename="seaborg_export.nc"'
            },
        )


def generate_conversation_summary(history: list[ChatTurn], model: str = "llama-3.1-8b-instant") -> str:
    import os
    from groq import Groq
    
    # Format the history textually for the LLM
    history_str = []
    for idx, turn in enumerate(history):
        history_str.append(f"Turn {idx+1}:")
        history_str.append(f"User Query: {turn.query}")
        history_str.append(f"SeaBorg Response: {turn.response}")
        history_str.append(f"Chart Type: {turn.chart_type} | Rows: {turn.rows_retrieved}")
    
    context = "\n".join(history_str)
    
    prompt = f"""You are summarizing an ocean research session using SeaBorg, an ARGO float data assistant. Write a concise 150-250 word research narrative covering: (1) what ocean regions or coordinates were investigated, (2) what variables were queried (temperature, salinity, depth, etc.), (3) key values and findings from the data, (4) any data gaps or refusals encountered and why. Write in third-person academic style suitable for a research appendix.

CONVERSATION HISTORY:
{context}"""

    client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=30.0)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        timeout=30.0,
    )
    return response.choices[0].message.content.strip()


def _generate_chart_image(turn) -> io.BytesIO | None:
    """
    Renders a matplotlib chart from a ChatTurn's data and chart_type.
    Returns a BytesIO PNG image buffer, or None if the chart cannot be generated.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    data = turn.data
    chart_type = turn.chart_type
    if not data or len(data) < 2:
        return None

    raw_df = pd.DataFrame(data)
    
    # Standardize column mappings cleanly without causing duplicate columns
    clean_cols = {}
    
    # We prioritize specific keys for each standardized field
    mapping_priorities = {
        "temp_c": ["temp_c", "temp", "temperature"],
        "depth_m": ["depth_m", "depth", "pressure"],
        "latitude": ["latitude", "lat"],
        "longitude": ["longitude", "lng", "lon"],
        "salinity": ["salinity"],
        "date": ["date"]
    }
    
    for standard_name, aliases in mapping_priorities.items():
        for alias in aliases:
            # Check if this alias is a column name (case-insensitive check)
            matched_col = next((c for c in raw_df.columns if c.lower() == alias), None)
            if matched_col is not None:
                clean_cols[standard_name] = raw_df[matched_col]
                break
                
    # Build clean DataFrame with unique columns
    df = pd.DataFrame(clean_cols)

    try:
        fig, ax = plt.subplots(figsize=(7, 4), dpi=120)
        fig.patch.set_facecolor("#0e1117")
        ax.set_facecolor("#0e1117")
        ax.tick_params(colors="#8a8fa3", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#2a2e3d")

        teal = "#00d4aa"
        ocean = "#00a8ff"

        if chart_type == "profile":
            # Depth profile: Depth (Y, inverted) vs Temperature or Salinity (X)
            q_lower = turn.query.lower()
            y_col = "salinity" if "salinity" in q_lower and "salinity" in df.columns else ("temp_c" if "temp_c" in df.columns else None)
            if "depth_m" in df.columns and y_col:
                df_clean = df.dropna(subset=["depth_m", y_col]).sort_values("depth_m")
                ax.scatter(df_clean[y_col].astype(float), df_clean["depth_m"].astype(float), 
                          c=teal, s=12, alpha=0.7, edgecolors="none")
                ax.plot(df_clean[y_col].astype(float), df_clean["depth_m"].astype(float), 
                       color=teal, alpha=0.4, linewidth=1)
                ax.invert_yaxis()
                label = "Salinity (PSU)" if y_col == "salinity" else "Temperature (°C)"
                ax.set_xlabel(label, color="#cbd0dc", fontsize=9)
                ax.set_ylabel("Depth (m)", color="#cbd0dc", fontsize=9)
                ax.set_title(f"Depth vs {label.split('(')[0].strip()}", color="#cbd0dc", fontsize=11, fontweight="bold")

        elif chart_type == "timeseries":
            # Timeseries: Date (X) vs Temperature or Salinity (Y)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).sort_values("date")
                q_lower = turn.query.lower()
                y_col = "salinity" if "salinity" in q_lower and "salinity" in df.columns else ("temp_c" if "temp_c" in df.columns else ("salinity" if "salinity" in df.columns else None))
                if y_col and y_col in df.columns:
                    df_clean = df.dropna(subset=[y_col])
                    ax.plot(df_clean["date"], df_clean[y_col].astype(float), color=teal, linewidth=1.2, alpha=0.8)
                    ax.scatter(df_clean["date"], df_clean[y_col].astype(float), c=teal, s=8, alpha=0.6, zorder=5)
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
                    fig.autofmt_xdate(rotation=30)
                    label = "Temperature (°C)" if y_col == "temp_c" else "Salinity (PSU)"
                    ax.set_xlabel("Date", color="#cbd0dc", fontsize=9)
                    ax.set_ylabel(label, color="#cbd0dc", fontsize=9)
                    ax.set_title(f"{label.split('(')[0].strip()} Over Time", color="#cbd0dc", fontsize=11, fontweight="bold")

        elif chart_type == "map":
            # Geographic scatter: Longitude (X) vs Latitude (Y)
            if "latitude" in df.columns and "longitude" in df.columns:
                df_clean = df.dropna(subset=["latitude", "longitude"])
                ax.scatter(df_clean["longitude"].astype(float), df_clean["latitude"].astype(float), 
                          c=teal, s=18, alpha=0.7, edgecolors=ocean, linewidths=0.5)
                ax.set_xlabel("Longitude", color="#cbd0dc", fontsize=9)
                ax.set_ylabel("Latitude", color="#cbd0dc", fontsize=9)
                ax.set_title("Float Positions", color="#cbd0dc", fontsize=11, fontweight="bold")
                ax.set_aspect("equal", adjustable="datalim")

        elif chart_type == "scatter":
            # General scatter: Temperature vs Salinity
            if "temp_c" in df.columns and "salinity" in df.columns:
                df_clean = df.dropna(subset=["temp_c", "salinity"])
                ax.scatter(df_clean["salinity"].astype(float), df_clean["temp_c"].astype(float), 
                          c=teal, s=12, alpha=0.6, edgecolors="none")
                ax.set_xlabel("Salinity (PSU)", color="#cbd0dc", fontsize=9)
                ax.set_ylabel("Temperature (°C)", color="#cbd0dc", fontsize=9)
                ax.set_title("Temperature vs Salinity", color="#cbd0dc", fontsize=11, fontweight="bold")

        elif chart_type == "ts_diagram":
            # T-S Diagram: Salinity (X) vs Temperature (Y)
            if "temp_c" in df.columns and "salinity" in df.columns:
                df_clean = df.dropna(subset=["temp_c", "salinity"])
                depth_col = "depth_m" if "depth_m" in df_clean.columns else None
                if depth_col and df_clean[depth_col].notna().any():
                    c_vals = df_clean[depth_col].astype(float)
                else:
                    c_vals = None
                scatter = ax.scatter(df_clean["salinity"].astype(float), df_clean["temp_c"].astype(float),
                                    c=c_vals, cmap="viridis_r" if c_vals is not None else None, s=14, alpha=0.7, edgecolors="none")
                if c_vals is not None:
                    cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
                    cbar.set_label("Depth (m)", color="#cbd0dc", fontsize=8)
                    cbar.ax.tick_params(colors="#8a8fa3", labelsize=7)
                ax.set_xlabel("Salinity (PSU)", color="#cbd0dc", fontsize=9)
                ax.set_ylabel("Temperature (°C)", color="#cbd0dc", fontsize=9)
                ax.set_title("T-S Diagram", color="#cbd0dc", fontsize=11, fontweight="bold")

        elif chart_type in ("3d_trajectory", "trajectory"):
            # Trajectory: Longitude (X) vs Latitude (Y)
            if "latitude" in df.columns and "longitude" in df.columns:
                if "date" in df.columns:
                    df = df.sort_values("date")
                df_clean = df.dropna(subset=["latitude", "longitude"])
                ax.plot(df_clean["longitude"].astype(float), df_clean["latitude"].astype(float), 
                        color=ocean, alpha=0.5, linewidth=1.5, zorder=1)
                ax.scatter(df_clean["longitude"].astype(float), df_clean["latitude"].astype(float), 
                          c=teal, s=16, alpha=0.8, edgecolors="none", zorder=2)
                if len(df_clean) >= 2:
                    ax.scatter(df_clean.iloc[0]["longitude"], df_clean.iloc[0]["latitude"], 
                               c="#ef4444", s=30, label="Start", zorder=3)
                    ax.scatter(df_clean.iloc[-1]["longitude"], df_clean.iloc[-1]["latitude"], 
                               c="#10b981", s=30, label="End", zorder=3)
                    ax.legend(loc="upper right", fontsize=8, facecolor="#0e1117", edgecolor="#2a2e3d", labelcolor="#cbd0dc")
                ax.set_xlabel("Longitude", color="#cbd0dc", fontsize=9)
                ax.set_ylabel("Latitude", color="#cbd0dc", fontsize=9)
                ax.set_title("Float Trajectory Journey", color="#cbd0dc", fontsize=11, fontweight="bold")
                ax.set_aspect("equal", adjustable="datalim")

        elif chart_type == "comparison":
            # Comparison: Bar chart comparing average values across floats
            if "float_id" in raw_df.columns:
                y_col = "salinity" if "salinity" in turn.query.lower() and "salinity" in df.columns else ("temp_c" if "temp_c" in df.columns else None)
                if y_col:
                    raw_df[y_col] = raw_df[y_col].astype(float)
                    grouped = raw_df.groupby("float_id")[y_col].mean().dropna()
                    if not grouped.empty:
                        bars = ax.bar([str(fid) for fid in grouped.index], grouped.values, color=teal, alpha=0.8, width=0.5)
                        ax.bar_label(bars, fmt='%.2f', color="#cbd0dc", fontsize=8)
                        label = "Salinity (PSU)" if y_col == "salinity" else "Temperature (°C)"
                        ax.set_xlabel("Float ID", color="#cbd0dc", fontsize=9)
                        ax.set_ylabel(f"Average {label}", color="#cbd0dc", fontsize=9)
                        ax.set_title(f"Comparison of Average {label.split('(')[0]}", color="#cbd0dc", fontsize=11, fontweight="bold")

        elif chart_type == "anomaly":
            # Anomaly: Line/Scatter plot highlighting points outside +/- 2 stddev
            y_col = "salinity" if "salinity" in turn.query.lower() and "salinity" in df.columns else ("temp_c" if "temp_c" in df.columns else None)
            if y_col and y_col in df.columns:
                y_vals = df[y_col].dropna().astype(float).values
                if len(y_vals) > 0:
                    mean = y_vals.mean()
                    std = y_vals.std() or 1.0
                    upper = mean + 2 * std
                    lower = mean - 2 * std
                    indices = range(len(y_vals))
                    ax.plot(indices, y_vals, color="#cbd0dc", alpha=0.3, linewidth=1)
                    normal_mask = (y_vals >= lower) & (y_vals <= upper)
                    ax.scatter([i for i in indices if normal_mask[i]], y_vals[normal_mask], c=teal, s=12, label="Normal", alpha=0.7)
                    ax.scatter([i for i in indices if not normal_mask[i]], y_vals[~normal_mask], c="#ef4444", s=20, label="Anomaly", zorder=5)
                    ax.axhline(mean, color=ocean, linestyle="--", alpha=0.5, label="Mean")
                    ax.axhline(upper, color="#ef4444", linestyle=":", alpha=0.5, label="+2 SD")
                    ax.axhline(lower, color="#ef4444", linestyle=":", alpha=0.5, label="-2 SD")
                    ax.legend(loc="upper right", fontsize=8, facecolor="#0e1117", edgecolor="#2a2e3d", labelcolor="#cbd0dc")
                    label = "Salinity (PSU)" if y_col == "salinity" else "Temperature (°C)"
                    ax.set_xlabel("Data Point Index", color="#cbd0dc", fontsize=9)
                    ax.set_ylabel(label, color="#cbd0dc", fontsize=9)
                    ax.set_title(f"{label.split('(')[0]} Anomaly Detection", color="#cbd0dc", fontsize=11, fontweight="bold")

        else:
            # Fallback
            if "depth_m" in df.columns and "temp_c" in df.columns:
                df_clean = df.dropna(subset=["depth_m", "temp_c"]).sort_values("depth_m")
                ax.scatter(df_clean["temp_c"].astype(float), df_clean["depth_m"].astype(float), c=teal, s=12, alpha=0.7)
                ax.invert_yaxis()
                ax.set_xlabel("Temperature (°C)", color="#cbd0dc", fontsize=9)
                ax.set_ylabel("Depth (m)", color="#cbd0dc", fontsize=9)
                ax.set_title("Data Visualization", color="#cbd0dc", fontsize=11, fontweight="bold")
            else:
                plt.close(fig)
                return None

        ax.grid(True, alpha=0.1, color="#ffffff")
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"[EXPORT] Chart generation failed: {e}", flush=True)
        try:
            plt.close(fig)
        except Exception:
            pass
        return None


def build_report_pdf(req: ExportReportRequest, summary_text: str | None = None) -> bytes:
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    TEAL = colors.HexColor("#00d4aa")
    OCEAN = colors.HexColor("#00a8ff")
    DARK_NAVY = colors.HexColor("#0a0c16")
    TEXT_COLOR = colors.HexColor("#2d3748")
    BORDER_COLOR = colors.HexColor("#e2e8f0")
    
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=DARK_NAVY,
        spaceAfter=5
    )
    
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4a5568"),
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        "Header1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=DARK_NAVY,
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=TEXT_COLOR,
        spaceAfter=6
    )
    
    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=TEXT_COLOR
    )
    
    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=colors.white
    )

    story = []
    
    # SECTION 1: HEADER
    story.append(Paragraph(req.title, title_style))
    meta_info = f"<b>Generated Date:</b> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')} | <b>Ocean Region Selected:</b> {req.ocean}"
    story.append(Paragraph(meta_info, subtitle_style))
    story.append(Spacer(1, 10))
    
    # SECTION 2: RESEARCH SUMMARY
    if summary_text:
        story.append(Paragraph("SECTION 1 — RESEARCH SUMMARY", h1_style))
        story.append(Paragraph(summary_text, body_style))
        story.append(Spacer(1, 15))
        
    # SECTION 3: CONVERSATION LOG
    story.append(Paragraph("SECTION 2 — CONVERSATION LOG", h1_style))
    for idx, turn in enumerate(req.history):
        turn_container = []
        turn_container.append(Paragraph(f"<b>Query {idx+1}:</b> {turn.query}", body_style))
        turn_container.append(Paragraph(f"<b>Response:</b> {turn.response}", body_style))
        
        meta_line = (
            f"<b>Chart Type:</b> {turn.chart_type} | "
            f"<b>Rows Retrieved:</b> {turn.rows_retrieved} | "
            f"<b>Status:</b> {turn.status.upper()}"
        )
        if turn.closest_distance_km is not None:
            meta_line += f" | <b>Distance:</b> {turn.closest_distance_km:.1f} km"
        if turn.refusal_type:
            meta_line += f" | <b>Refusal Type:</b> {turn.refusal_type}"
            
        turn_container.append(Paragraph(meta_line, body_style))
        turn_container.append(Spacer(1, 8))
        
        # Generate and embed chart image if applicable
        if turn.chart_type not in ("none", "summary") and turn.data and len(turn.data) >= 2:
            chart_img = _generate_chart_image(turn)
            if chart_img:
                from reportlab.platypus import Image
                turn_container.append(Image(chart_img, width=480, height=280))
                turn_container.append(Spacer(1, 8))
        
        story.append(KeepTogether(turn_container))
        
    # SECTION 4: RETRIEVED DATA APPENDIX
    if req.include_data:
        story.append(Spacer(1, 10))
        story.append(Paragraph("SECTION 3 — RETRIEVED DATA APPENDIX", h1_style))
        
        has_data = False
        for idx, turn in enumerate(req.history):
            if turn.status == "ok" and turn.data:
                has_data = True
                story.append(Paragraph(f"<b>Retrieved Rows for Query {idx+1} ({turn.query[:45]}...):</b>", body_style))
                
                headers = ["Float ID", "Date", "Lat", "Lon", "Depth (m)", "Temp (°C)", "Salinity (PSU)", "Dist (km)"]
                table_data = [[Paragraph(h, table_header_style) for h in headers]]
                
                for row in turn.data[:15]:
                    temp_val = f"{row.get('temp', row.get('temp_c', 'N/A')):.1f}" if isinstance(row.get('temp', row.get('temp_c')), (int, float)) else "N/A"
                    sal_val = f"{row.get('salinity', 'N/A'):.2f}" if isinstance(row.get('salinity'), (int, float)) else "N/A"
                    dist_val = f"{row.get('distance_km', 'N/A'):.1f}" if isinstance(row.get('distance_km'), (int, float)) else "N/A"
                    
                    r_data = [
                        str(row.get("float_id", "N/A") or "N/A"),
                        str(row.get("date", "N/A") or "N/A")[:10],
                        f"{float(lat_v):.2f}" if (lat_v := row.get('lat', row.get('latitude'))) is not None else "N/A",
                        f"{float(lon_v):.2f}" if (lon_v := row.get('lng', row.get('longitude'))) is not None else "N/A",
                        f"{float(dep_v):.0f}" if (dep_v := row.get('depth', row.get('depth_m'))) is not None else "N/A",
                        temp_val,
                        sal_val,
                        dist_val
                    ]
                    table_data.append([Paragraph(str(cell), table_cell_style) for cell in r_data])
                    
                t = Table(table_data, colWidths=[55, 60, 50, 50, 50, 55, 65, 55])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), DARK_NAVY),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('BOTTOMPADDING', (0,0), (-1,0), 4),
                    ('TOPPADDING', (0,0), (-1,0), 4),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
                    ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
                    ('BOTTOMPADDING', (0,1), (-1,-1), 3),
                    ('TOPPADDING', (0,1), (-1,-1), 3),
                ]))
                story.append(t)
                story.append(Spacer(1, 10))
                
                if len(turn.data) > 15:
                    story.append(Paragraph(f"<i>* Showing top 15 of {len(turn.data)} rows retrieved.</i>", body_style))
                    story.append(Spacer(1, 8))
                    
        if not has_data:
            story.append(Paragraph("No valid data rows retrieved in this conversation session.", body_style))
            
    # SECTION 5: FOOTER
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>DATA SOURCE & PIPELINE ATTRIBUTION</b>", h1_style))
    story.append(Paragraph("<b>Data Source:</b> Data sourced from ARGO Global Float Array via SeaBorg RAG pipeline.", body_style))
    
    # Collect all unique float IDs in report history
    unique_fids = set()
    for turn in req.history:
        if turn.float_ids:
            for fid in turn.float_ids:
                if fid and fid.strip():
                    unique_fids.add(fid.strip())
    source_files = [f"{fid}_prof.nc" for fid in sorted(unique_fids)]
    if source_files:
        files_str = ", ".join(source_files)
        story.append(Paragraph(f"<b>Source NetCDF Files:</b> {files_str}", body_style))
        
    story.append(Paragraph("<b>Pipeline Info:</b> Retrieval: FAISS vector index + PostgreSQL | LLM: Llama-3.1-8b-instant via Groq API.", body_style))
    story.append(Paragraph(f"<b>Configuration:</b> Similarity threshold: {SIMILARITY_THRESHOLD:.2f} | Distance guard: 500km.", body_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def build_report_csvs(req: ExportReportRequest) -> tuple[str, str | None]:
    import csv
    import io
    
    main_buffer = io.StringIO()
    writer = csv.writer(main_buffer)
    writer.writerow([
        "query", "response", "chart_type", "rows_retrieved", "float_ids",
        "status", "refusal_type", "closest_distance_km", "timestamp"
    ])
    
    for turn in req.history:
        writer.writerow([
            turn.query,
            turn.response,
            turn.chart_type,
            turn.rows_retrieved,
            ",".join(turn.float_ids),
            turn.status,
            turn.refusal_type or "",
            f"{turn.closest_distance_km:.2f}" if turn.closest_distance_km is not None else "",
            str(turn.timestamp or "")
        ])
    
    main_csv = main_buffer.getvalue()
    
    data_csv = None
    if req.include_data:
        data_buffer = io.StringIO()
        d_writer = csv.writer(data_buffer)
        d_writer.writerow([
            "query_index", "float_id", "date", "latitude", "longitude",
            "depth_m", "temp_c", "salinity", "distance_km"
        ])
        
        for idx, turn in enumerate(req.history):
            if turn.status == "ok" and turn.data:
                for row in turn.data:
                    d_writer.writerow([
                        idx + 1,
                        row.get("float_id", ""),
                        row.get("date", ""),
                        row.get("lat", row.get("latitude", "")),
                        row.get("lng", row.get("longitude", "")),
                        row.get("depth", row.get("depth_m", "")),
                        row.get("temp", row.get("temp_c", "")),
                        row.get("salinity", ""),
                        row.get("distance_km", "")
                    ])
        data_csv = data_buffer.getvalue()
        
    return main_csv, data_csv


def build_single_csv(req: ExportReportRequest) -> str:
    import csv
    import io
    
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    
    if req.include_data:
        writer.writerow([
            "query", "response", "chart_type", "rows_retrieved", "float_ids",
            "status", "refusal_type", "closest_distance_km", "timestamp",
            "float_id", "date", "latitude", "longitude", "depth_m", "temp_c",
            "salinity", "distance_km"
        ])
        
        for turn in req.history:
            if turn.status == "ok" and turn.data:
                for row in turn.data:
                    writer.writerow([
                        turn.query,
                        turn.response,
                        turn.chart_type,
                        turn.rows_retrieved,
                        ",".join(turn.float_ids),
                        turn.status,
                        turn.refusal_type or "",
                        f"{turn.closest_distance_km:.2f}" if turn.closest_distance_km is not None else "",
                        str(turn.timestamp or ""),
                        row.get("float_id", ""),
                        row.get("date", ""),
                        row.get("lat", row.get("latitude", "")),
                        row.get("lng", row.get("longitude", "")),
                        row.get("depth", row.get("depth_m", "")),
                        row.get("temp", row.get("temp_c", "")),
                        row.get("salinity", ""),
                        row.get("distance_km", "")
                    ])
            else:
                writer.writerow([
                    turn.query,
                    turn.response,
                    turn.chart_type,
                    turn.rows_retrieved,
                    ",".join(turn.float_ids),
                    turn.status,
                    turn.refusal_type or "",
                    f"{turn.closest_distance_km:.2f}" if turn.closest_distance_km is not None else "",
                    str(turn.timestamp or ""),
                    "", "", "", "", "", "", "", ""
                ])
    else:
        writer.writerow([
            "query", "response", "chart_type", "rows_retrieved", "float_ids",
            "status", "refusal_type", "closest_distance_km", "timestamp"
        ])
        for turn in req.history:
            writer.writerow([
                turn.query,
                turn.response,
                turn.chart_type,
                turn.rows_retrieved,
                ",".join(turn.float_ids),
                turn.status,
                turn.refusal_type or "",
                f"{turn.closest_distance_km:.2f}" if turn.closest_distance_km is not None else "",
                str(turn.timestamp or "")
            ])
            
    return buffer.getvalue()


@router.post("/export_report")
def export_report(req: ExportReportRequest):
    """
    Generates a PDF and/or CSVs based on options, and packages into a ZIP or returns the single format.
    """
    summary_text = None
    if req.include_summary and req.history:
        try:
            was_truncated = len(req.history) > 10
            truncated_history = req.history[-10:] if was_truncated else req.history
            summary_text = generate_conversation_summary(truncated_history)
            if was_truncated:
                summary_text = "(Summary based on most recent 10 queries)\n\n" + summary_text
        except Exception as e:
            summary_text = f"Error generating research summary: {e}"

    import zipfile
    import io
    import time
    
    timestamp_str = time.strftime("%Y-%m-%d_%H%M%S")
    
    if req.format == "pdf":
        pdf_bytes = build_report_pdf(req, summary_text)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="seaborg_report_{timestamp_str}.pdf"'}
        )
        
    elif req.format == "csv":
        single_csv = build_single_csv(req)
        return Response(
            content=single_csv.encode('utf-8'),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="seaborg_report_{timestamp_str}.csv"'}
        )
            
    else: # "both"
        pdf_bytes = build_report_pdf(req, summary_text)
        main_csv, data_csv = build_report_csvs(req)
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr(f"seaborg_report_{timestamp_str}.pdf", pdf_bytes)
            zip_file.writestr(f"seaborg_report_{timestamp_str}.csv", main_csv)
            if data_csv:
                zip_file.writestr(f"argo_data_{timestamp_str}.csv", data_csv)
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="seaborg_report_{timestamp_str}.zip"'}
        )