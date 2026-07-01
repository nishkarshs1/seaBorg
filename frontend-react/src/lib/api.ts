import axios from "axios";
import {
  mockStats,
  mockFloats,
  mockChatResponse,
  type Stats,
  type Float,
  type ChatResponse,
} from "./mocks";

const API_URL =
  (typeof process !== "undefined" ? process.env?.VITE_API_URL : null) ||
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8001";

const api = axios.create({
  baseURL: API_URL,
  timeout: 5000,
});

// Chat needs a long timeout — Groq rate-limit retries can sleep up to 15s per attempt
const chatApi = axios.create({
  baseURL: API_URL,
  timeout: 120000,
});

async function safe<T>(fn: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await fn();
  } catch {
    return fallback;
  }
}

export const getHealth = () =>
  safe(async () => (await api.get("/health")).data as { status: string; service: string }, {
    status: "error",
    service: "seaborg-api",
  });

// Backend GET /api/stats returns:
// { total_rows, earliest_date, latest_date, unique_floats, avg_temp, max_depth, lat_min, lat_max, lon_min, lon_max }
// Frontend Stats type only uses: total_rows, unique_floats, earliest_date, latest_date
export const getStats = () =>
  safe<Stats | null>(async () => {
    const raw = (await api.get("/api/stats")).data;
    return {
      total_rows: raw.total_rows,
      unique_floats: raw.unique_floats,
      earliest_date: raw.earliest_date,
      latest_date: raw.latest_date,
    };
  }, null);

// Backend GET /api/floats?page=1&page_size=100 returns:
// { total, page, page_size, floats: [{ float_id, first_seen, last_seen, lat_min, lat_max, lon_min, lon_max, record_count, avg_temp, max_depth }] }
// Frontend expects Float[] = [{ id, lat, lng, depth, temp, salinity, last_reading }]
// We transform the backend shape into the frontend shape
export const getFloats = (limit = 100) =>
  safe<Float[]>(async () => {
    const res = (await api.get("/api/floats", { params: { page: 1, page_size: limit } })).data;
    return (res.floats || []).map(
      (f: {
        float_id: string;
        lat_min: number;
        lat_max: number;
        lon_min: number;
        lon_max: number;
        max_depth: number;
        avg_temp: number;
        record_count: number;
        last_seen: string;
      }) => ({
        id: String(f.float_id),
        lat: +((f.lat_min + f.lat_max) / 2).toFixed(3),
        lng: +((f.lon_min + f.lon_max) / 2).toFixed(3),
        depth: Math.round(f.max_depth ?? 0),
        temp: +(f.avg_temp ?? 0).toFixed(2),
        salinity: 34.5, // not returned by backend; use reasonable default
        last_reading: String(f.last_seen ?? "").slice(0, 10),
      }),
    );
  }, []);

// Backend POST /api/chat returns:
// { answer, chart_type ("map"|"profile"|"timeseries"|"none"), float_ids, sql_used, confidence }
// Frontend ChatResponse expects: { answer, chart_type, sql_used, data, float_ids? }
// Backend does NOT return a `data` array. We map "none" -> generate empty data.
export const postChat = (
  message: string,
  ocean?: string,
  history?: Array<{ role: string; text: string }>,
) =>
  safe<ChatResponse>(
    async () => {
      const raw = (await chatApi.post("/api/chat", { message, ocean, history })).data;
      return {
        answer: raw.answer,
        chart_type: raw.chart_type,
        sql_used: raw.sql_used,
        data: raw.data ?? [], // pass through backend serialized chart data
        float_ids: raw.float_ids ?? [],
      };
    },
    {
      answer:
        "The server is taking longer than expected (possibly due to API rate limiting). Please try again in a moment.",
      chart_type: "none",
      sql_used: "-- Request timed out",
      data: [],
      float_ids: [],
    },
  );

export const getFloatDetail = (floatId: string) =>
  safe<any[]>(async () => {
    return (await api.get(`/api/float/${floatId}`)).data;
  }, []);

// Backend POST /api/export accepts:
// { float_ids: string[], format: "csv"|"netcdf", start_date?, end_date? }
// Returns a file stream download
export const exportData = async (floatIds: string[], format: "csv" | "netcdf" = "csv") => {
  const res = await api.post(
    "/api/export",
    { float_ids: floatIds, format },
    { responseType: "blob" },
  );
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = format === "csv" ? "seaborg_export.csv" : "seaborg_export.nc";
  a.click();
  URL.revokeObjectURL(url);
};
