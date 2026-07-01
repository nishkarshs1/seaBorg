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
                        str(row.get("float_id", "N/A")),
                        str(row.get("date", "N/A"))[:10],
                        f"{row.get('lat', row.get('latitude', 0.0)):.2f}",
                        f"{row.get('lng', row.get('longitude', 0.0)):.2f}",
                        f"{row.get('depth', row.get('depth_m', 0.0)):.0f}",
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