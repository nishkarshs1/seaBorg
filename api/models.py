from typing import Literal
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    ocean: str | None = None
    history: list[dict] | None = None


class ChatResponse(BaseModel):
    answer: str
    chart_type: Literal["map", "profile", "timeseries", "ts_diagram", "3d_trajectory", "comparison", "anomaly", "summary", "none"]
    float_ids: list[str]
    sql_used: str
    confidence: float
    data: list[dict] = []


class FloatDataRequest(BaseModel):
    float_id: str
    start_date: str | None = None
    end_date: str | None = None
    depth_min: float | None = None
    depth_max: float | None = None


class ExportRequest(BaseModel):
    float_ids: list[str]
    format: Literal["csv", "netcdf"]
    start_date: str | None = None
    end_date: str | None = None


class ChatTurn(BaseModel):
    query: str
    response: str
    chart_type: str
    rows_retrieved: int
    float_ids: list[str] = []
    status: str
    refusal_type: str | None = None
    closest_distance_km: float | None = None
    data: list[dict] = []
    timestamp: float | str | None = None


class ExportReportRequest(BaseModel):
    title: str
    include_data: bool
    include_summary: bool
    format: Literal["pdf", "csv", "both"]
    ocean: str = "All Oceans"
    history: list[ChatTurn]