export type Stats = {
  total_rows: number;
  unique_floats: number;
  earliest_date: string;
  latest_date: string;
};

export type Float = {
  id: string;
  lat: number;
  lng: number;
  depth: number;
  temp: number;
  salinity: number;
  last_reading: string;
};

export type ChatResponse = {
  answer: string;
  chart_type: "profile" | "map" | "timeseries" | "scatter";
  sql_used: string;
  data: Array<Record<string, number | string>>;
  float_ids?: string[];
};

export const mockStats: Stats = {
  total_rows: 694182,
  unique_floats: 43,
  earliest_date: "2002-11-11",
  latest_date: "2026-06-08",
};

function rand(seed: number) {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

export const mockFloats: Float[] = Array.from({ length: 100 }, (_, i) => {
  const r1 = rand(i + 1);
  const r2 = rand(i * 2.7 + 3);
  const r3 = rand(i * 5.1 + 7);
  const region = i % 3;
  const lat = -55 + r1 * 110;
  let lng: number;
  if (region === 0) lng = -60 + r2 * 50;
  else if (region === 1) lng = -180 + r2 * 90;
  else lng = 50 + r2 * 50;
  const depth = Math.round(50 + r3 * 1950);
  const temp = +(2 + (30 - depth / 80) * rand(i + 11)).toFixed(2);
  const salinity = +(33 + r1 * 3).toFixed(2);
  const day = Math.floor(r2 * 28) + 1;
  return {
    id: `ARGO-${2900000 + i}`,
    lat: +lat.toFixed(3),
    lng: +lng.toFixed(3),
    depth,
    temp,
    salinity,
    last_reading: `2025-${String((i % 12) + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`,
  };
});

function profile(): ChatResponse["data"] {
  return Array.from({ length: 20 }, (_, i) => {
    const depth = (i + 1) * 100;
    const temp = +(22 * Math.exp(-depth / 500) + 2 + rand(i + 99) * 0.4).toFixed(2);
    return { depth, temp };
  });
}

function timeseries(): ChatResponse["data"] {
  return Array.from({ length: 24 }, (_, i) => {
    const month = (i % 12) + 1;
    const year = 2024 + Math.floor(i / 12);
    return {
      date: `${year}-${String(month).padStart(2, "0")}-15`,
      temp: +(15 + Math.sin(i / 3) * 4 + rand(i + 1) * 0.6).toFixed(2),
    };
  });
}

export function mockChatResponse(message: string): ChatResponse {
  const m = message.toLowerCase();
  if (m.includes("time") || m.includes("trend") || m.includes("month")) {
    return {
      answer:
        "Here's the monthly temperature trend across active North Atlantic floats over the last 24 months. Notice the seasonal oscillation between winter lows (~11°C) and summer peaks (~19°C).",
      chart_type: "timeseries",
      sql_used:
        "SELECT date_trunc('month', reading_date) AS month,\n       AVG(temperature) AS temp\nFROM ocean_readings\nWHERE region = 'north_atlantic'\n  AND reading_date >= NOW() - INTERVAL '24 months'\nGROUP BY 1\nORDER BY 1;",
      data: timeseries(),
      float_ids: mockFloats.slice(0, 8).map((f) => f.id),
    };
  }
  if (m.includes("map") || m.includes("location") || m.includes("where")) {
    return {
      answer: `Plotting ${mockFloats.length} active floats across the Atlantic, Pacific, and Indian oceans. Markers are color-coded by surface temperature.`,
      chart_type: "map",
      sql_used:
        "SELECT float_id, lat, lng, surface_temp\nFROM ocean_floats\nWHERE status = 'active'\nORDER BY last_reading DESC\nLIMIT 100;",
      data: mockFloats.map((f) => ({
        id: f.id,
        lat: f.lat,
        lng: f.lng,
        temp: f.temp,
      })),
      float_ids: mockFloats.slice(0, 12).map((f) => f.id),
    };
  }
  return {
    answer:
      "Vertical temperature profile retrieved from float ARGO-2900007. Surface waters sit around 22°C; the thermocline drops sharply between 200–800 m before stabilizing near 2°C in the deep ocean.",
    chart_type: "profile",
    sql_used:
      "SELECT depth_m AS depth,\n       AVG(temperature) AS temp\nFROM ocean_readings\nWHERE float_id = 'ARGO-2900007'\n  AND reading_date >= '2025-01-01'\nGROUP BY depth_m\nORDER BY depth_m ASC;",
    data: profile(),
    float_ids: ["ARGO-2900007"],
  };
}

export const histogramTemp = Array.from(
  { length: 400 },
  (_, i) => +(8 + Math.sin(i / 12) * 3 + (rand(i + 5) - 0.5) * 6).toFixed(2),
);

export const histogramDepth = [
  { bucket: "0–200m", n: 84 },
  { bucket: "200–500m", n: 142 },
  { bucket: "500–1000m", n: 196 },
  { bucket: "1000–1500m", n: 168 },
  { bucket: "1500–2000m", n: 121 },
  { bucket: "2000m+", n: 58 },
];

export const tsDiagram = Array.from({ length: 220 }, (_, i) => {
  const depth = Math.round(rand(i + 1) * 2000);
  const temp = +(2 + (2000 - depth) / 100 + (rand(i + 7) - 0.5) * 2).toFixed(2);
  const sal = +(34 + (rand(i + 13) - 0.5) * 1.4).toFixed(2);
  return { temp, sal, depth };
});

export const timeseriesAnalytics = Array.from({ length: 60 }, (_, i) => ({
  date: new Date(2022, 0, i * 14).toISOString().slice(0, 10),
  temp: +(14 + Math.sin(i / 5) * 3 + (rand(i + 2) - 0.5) * 0.8).toFixed(2),
}));

export const sparklineData = Array.from({ length: 32 }, (_, i) => ({
  x: i,
  y: +(40 + Math.sin(i / 2) * 18 + rand(i) * 14).toFixed(1),
}));
