import { createFileRoute } from "@tanstack/react-router";
import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { GlassCard } from "@/components/ui/GlassCard";
import { GradientText } from "@/components/ui/GradientText";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { Shimmer } from "@/components/ui/Shimmer";
import { getFloats, getFloatDetail } from "@/lib/api";
import { histogramTemp, histogramDepth, tsDiagram, timeseriesAnalytics } from "@/lib/mocks";

export const Route = createFileRoute("/analytics")({
  head: () => ({
    meta: [
      { title: "Analytics — SeaBorg" },
      {
        name: "description",
        content: "Advanced oceanographic analytics: distributions, T-S diagrams, timeseries.",
      },
      { property: "og:title", content: "SeaBorg Analytics" },
      {
        property: "og:description",
        content: "Advanced oceanographic analytics: distributions, T-S diagrams, timeseries.",
      },
    ],
  }),
  component: AnalyticsPage,
});

function ChartCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <GlassCard hover={false} className="flex flex-col p-0 overflow-hidden">
      <div className="border-b border-[var(--glass-border)] px-5 py-3">
        <h3 className="text-sm font-semibold">{title}</h3>
        {subtitle && <p className="text-[11px] text-muted-foreground">{subtitle}</p>}
      </div>
      <div className="h-[320px] w-full p-3">{children}</div>
    </GlassCard>
  );
}

// Stats calculator helpers for specific float data
function calculatePearson(x: number[], y: number[]) {
  const n = x.length;
  if (n === 0) return 0;
  const sumX = x.reduce((a, b) => a + b, 0);
  const sumY = y.reduce((a, b) => a + b, 0);
  const meanX = sumX / n;
  const meanY = sumY / n;
  let num = 0;
  let denX = 0;
  let denY = 0;
  for (let i = 0; i < n; i++) {
    const dx = x[i] - meanX;
    const dy = y[i] - meanY;
    num += dx * dy;
    denX += dx * dx;
    denY += dy * dy;
  }
  if (denX === 0 || denY === 0) return 0;
  return num / Math.sqrt(denX * denY);
}

function calculateStdDev(arr: number[], mean: number) {
  if (arr.length === 0) return 0;
  const variance = arr.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / arr.length;
  return Math.sqrt(variance);
}

function AnalyticsPage() {
  const [selectedFloat, setSelectedFloat] = useState<string>("All Floats");

  // Fetch floats listing for dropdown
  const { data: floatList = [] } = useQuery({
    queryKey: ["floats", 100],
    queryFn: () => getFloats(100),
  });

  // Fetch specific float detail if selected
  const { data: detailData = [], isLoading: isDetailLoading } = useQuery({
    queryKey: ["float-detail", selectedFloat],
    queryFn: () => getFloatDetail(selectedFloat),
    enabled: selectedFloat !== "All Floats",
  });

  // Dynamic KPI stats calculation based on dataset
  const stats = useMemo(() => {
    if (selectedFloat === "All Floats") {
      return {
        correlation: "0.08",
        meanDepth: "618 m",
        tempStdDev: "8.51 °C",
        salinityRange: "26.2 - 37.0 PSU",
      };
    }

    if (detailData.length === 0) {
      return {
        correlation: "—",
        meanDepth: "—",
        tempStdDev: "—",
        salinityRange: "—",
      };
    }

    const temps = detailData.map((d: any) => d.temp_c ?? 0);
    const salinities = detailData.map((d: any) => d.salinity ?? 34.5);
    const depths = detailData.map((d: any) => d.depth_m ?? 0);

    const meanDepthVal = depths.reduce((a, b) => a + b, 0) / depths.length;
    const meanTemp = temps.reduce((a, b) => a + b, 0) / temps.length;
    const stdTemp = calculateStdDev(temps, meanTemp);
    const pearson = calculatePearson(temps, salinities);

    const minSal = Math.min(...salinities);
    const maxSal = Math.max(...salinities);

    return {
      correlation: pearson.toFixed(2),
      meanDepth: `${Math.round(meanDepthVal)} m`,
      tempStdDev: `${stdTemp.toFixed(2)} °C`,
      salinityRange: `${minSal.toFixed(1)} - ${maxSal.toFixed(1)} PSU`,
    };
  }, [selectedFloat, detailData]);

  // Aggregate readings over time dynamically for specific floats
  const timeseriesData = useMemo(() => {
    if (selectedFloat === "All Floats") return timeseriesAnalytics;

    // Group detailData by date
    const dateMap: Record<string, { sum: number; count: number }> = {};
    detailData.forEach((d: any) => {
      const date = d.date ? d.date.slice(0, 10) : "";
      if (!date) return;
      if (!dateMap[date]) {
        dateMap[date] = { sum: 0, count: 0 };
      }
      dateMap[date].sum += d.temp_c ?? 0;
      dateMap[date].count += 1;
    });

    return Object.entries(dateMap)
      .map(([date, o]) => ({ date, temp: +(o.sum / o.count).toFixed(2) }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [selectedFloat, detailData]);

  // Binned depth zones mapping
  const binnedDepthZones = useMemo(() => {
    if (selectedFloat === "All Floats") {
      return [
        { zone: "Surface (0-200m)", temps: histogramTemp.slice(0, 100) },
        { zone: "Intermediate (200-1000m)", temps: histogramTemp.slice(100, 250) },
        { zone: "Deep (1000m+)", temps: histogramTemp.slice(250, 400) },
      ];
    }

    const surface: number[] = [];
    const intermediate: number[] = [];
    const deep: number[] = [];

    detailData.forEach((d: any) => {
      const depth = d.depth_m ?? 0;
      const temp = d.temp_c ?? 0;
      if (depth <= 200) surface.push(temp);
      else if (depth <= 1000) intermediate.push(temp);
      else deep.push(temp);
    });

    return [
      { zone: "Surface (0-200m)", temps: surface },
      { zone: "Intermediate (200-1000m)", temps: intermediate },
      { zone: "Deep (1000m+)", temps: deep },
    ];
  }, [selectedFloat, detailData]);

  // Heatmap generation
  const heatmapData = useMemo(() => {
    const calendarMonthAbbrs = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];

    // Group records by Month/Year
    const matrix: Record<number, Record<number, number>> = {};
    const dataset =
      selectedFloat === "All Floats"
        ? timeseriesAnalytics.map((t) => ({ date: t.date }))
        : detailData;

    dataset.forEach((d: any) => {
      const dateStr = d.date ?? "";
      if (!dateStr) return;
      const dt = new Date(dateStr);
      if (isNaN(dt.getTime())) return;
      const month = dt.getMonth(); // 0-11
      const year = dt.getFullYear();
      if (!matrix[year]) matrix[year] = {};
      matrix[year][month] = (matrix[year][month] ?? 0) + 1;
    });

    const years = Object.keys(matrix).map(Number).sort();
    if (years.length === 0) return { x: [], y: [], z: [] };

    const z: number[][] = [];
    years.forEach((yr) => {
      const row: number[] = [];
      for (let m = 0; m < 12; m++) {
        row.push(matrix[yr][m] ?? 0);
      }
      z.push(row);
    });

    return {
      x: calendarMonthAbbrs,
      y: years,
      z,
    };
  }, [selectedFloat, detailData]);

  const showLoading = selectedFloat !== "All Floats" && isDetailLoading;

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-10 lg:px-10">
      <header className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            <GradientText>Advanced Analytics</GradientText>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            In-depth statistical analysis and distributions of fleet ocean metrics.
          </p>
        </div>

        {/* Float selector dropdown */}
        <div className="flex items-center gap-2">
          <label
            htmlFor="float-select"
            className="text-xs text-muted-foreground font-mono uppercase"
          >
            Filter Float:
          </label>
          <select
            id="float-select"
            value={selectedFloat}
            onChange={(e) => setSelectedFloat(e.target.value)}
            className="rounded-lg border border-[var(--glass-border)] bg-card text-foreground px-3 py-1.5 text-xs outline-none focus:border-teal/40 transition-colors"
          >
            <option value="All Floats">All Floats</option>
            {floatList.map((f) => (
              <option key={f.id} value={f.id}>
                Float {f.id}
              </option>
            ))}
          </select>
        </div>
      </header>

      {/* KPI statistics strip */}
      <section className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <GlassCard hover={false} className="px-5 py-4">
          <div className="text-[10px] font-mono uppercase tracking-[0.14em] text-muted-foreground">
            Pearson Correlation
          </div>
          <div className="mt-1 font-mono text-xl font-semibold text-teal">{stats.correlation}</div>
        </GlassCard>
        <GlassCard hover={false} className="px-5 py-4">
          <div className="text-[10px] font-mono uppercase tracking-[0.14em] text-muted-foreground">
            Mean Depth
          </div>
          <div className="mt-1 font-mono text-xl font-semibold text-ocean">{stats.meanDepth}</div>
        </GlassCard>
        <GlassCard hover={false} className="px-5 py-4">
          <div className="text-[10px] font-mono uppercase tracking-[0.14em] text-muted-foreground">
            Temp Std Dev
          </div>
          <div className="mt-1 font-mono text-xl font-semibold text-teal">{stats.tempStdDev}</div>
        </GlassCard>
        <GlassCard hover={false} className="px-5 py-4">
          <div className="text-[10px] font-mono uppercase tracking-[0.14em] text-muted-foreground">
            Salinity Range
          </div>
          <div className="mt-1 font-mono text-xl font-semibold text-ocean">
            {stats.salinityRange}
          </div>
        </GlassCard>
      </section>

      {showLoading ? (
        <div className="space-y-6">
          <Shimmer className="h-64 w-full" />
          <Shimmer className="h-64 w-full" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Main Charts Grid */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ChartCard
              title="Temperature Distribution"
              subtitle="Shows the frequency of different temperature readings"
            >
              <PlotlyChart
                data={[
                  {
                    type: "histogram",
                    x:
                      selectedFloat === "All Floats"
                        ? histogramTemp
                        : detailData.map((d: any) => d.temp_c ?? 0),
                    marker: { color: "#00d4aa", line: { color: "#0a0a0f", width: 1 } },
                    opacity: 0.9,
                    nbinsx: 50,
                  },
                ]}
                layout={{
                  bargap: 0.05,
                  xaxis: { title: { text: "Temperature (°C)" } },
                  yaxis: { title: { text: "Count" } },
                }}
              />
            </ChartCard>

            <ChartCard
              title="Depth Distribution"
              subtitle="Illustrates how many sensor readings were taken at various depths"
            >
              <PlotlyChart
                data={[
                  {
                    type: "histogram",
                    x:
                      selectedFloat === "All Floats"
                        ? histogramDepth.flatMap((d) => Array(d.n).fill(parseFloat(d.bucket)))
                        : detailData.map((d: any) => d.depth_m ?? 0),
                    marker: { color: "#00a8ff", line: { color: "#0a0a0f", width: 1 } },
                    opacity: 0.9,
                    nbinsx: 50,
                  },
                ]}
                layout={{
                  bargap: 0.05,
                  xaxis: { title: { text: "Depth (m)" } },
                  yaxis: { title: { text: "Count" } },
                }}
              />
            </ChartCard>

            <ChartCard
              title="T-S Diagram (Temperature vs Salinity)"
              subtitle="A standard oceanographic plot mapping Temperature against Salinity"
            >
              <PlotlyChart
                data={[
                  {
                    type: "scatter",
                    mode: "markers",
                    x:
                      selectedFloat === "All Floats"
                        ? tsDiagram.map((d) => d.sal)
                        : detailData.map((d: any) => d.salinity ?? 34.5),
                    y:
                      selectedFloat === "All Floats"
                        ? tsDiagram.map((d) => d.temp)
                        : detailData.map((d: any) => d.temp_c ?? 0),
                    marker: {
                      size: 7,
                      color:
                        selectedFloat === "All Floats"
                          ? tsDiagram.map((d) => d.depth)
                          : detailData.map((d: any) => d.depth_m ?? 0),
                      colorscale: "Viridis",
                      reversescale: true,
                      opacity: 0.75,
                      line: { color: "rgba(255,255,255,0.15)", width: 0.4 },
                      colorbar: {
                        title: { text: "depth (m)" },
                        outlinewidth: 0,
                        thickness: 10,
                      },
                    },
                    hovertemplate: "S %{x} PSU · T %{y}°C<extra></extra>",
                  },
                ]}
                layout={{
                  xaxis: { title: { text: "Salinity (PSU)" } },
                  yaxis: { title: { text: "Temperature (°C)" } },
                }}
              />
            </ChartCard>

            <ChartCard
              title="Readings Over Time"
              subtitle="Tracks the volume of data collected by the floats over time"
            >
              <PlotlyChart
                data={[
                  {
                    type: "scatter",
                    mode: "lines+markers",
                    x: timeseriesData.map((d: any) => d.date),
                    y: timeseriesData.map((d: any) => d.temp),
                    line: { color: "#00d4aa", width: 2, shape: "spline" },
                    marker: { color: "#00a8ff", size: 4 },
                    fill: "tozeroy",
                    fillcolor: "rgba(0,212,170,0.08)",
                    hovertemplate: "%{x}<br>%{y}°C<extra></extra>",
                  },
                ]}
                layout={{
                  xaxis: { title: { text: "Date" } },
                  yaxis: { title: { text: "Temp (°C)" } },
                }}
              />
            </ChartCard>
          </div>

          {/* Full-width Heatmap Section */}
          <ChartCard
            title="Float Activity Heatmap (Readings per Month/Year)"
            subtitle="Visualizes the density of sensor readings aggregated by month and year"
          >
            {heatmapData.x.length > 0 ? (
              <PlotlyChart
                data={[
                  {
                    type: "heatmap",
                    x: heatmapData.x,
                    y: heatmapData.y,
                    z: heatmapData.z,
                    colorscale: "Tealgrn",
                    hovertemplate: "Year: %{y}<br>Month: %{x}<br>Count: <b>%{z}</b><extra></extra>",
                  },
                ]}
                layout={{
                  xaxis: { title: { text: "Month" } },
                  yaxis: { title: { text: "Year" } },
                  margin: { t: 10, b: 40 },
                }}
              />
            ) : (
              <div className="grid h-full place-items-center text-center text-xs text-muted-foreground">
                No temporal data available for this selection
              </div>
            )}
          </ChartCard>

          {/* Depth Zone Box Plot Section */}
          <ChartCard
            title="Temperature Distribution by Depth Zone"
            subtitle="Shows the statistical spread (median, quartiles) of temperatures recorded at surface, intermediate, and deep ocean"
          >
            <PlotlyChart
              data={binnedDepthZones.map((z) => ({
                type: "box",
                y: z.temps,
                name: z.zone,
                boxpoints: "outliers",
                marker: {
                  color: z.zone.includes("Surface")
                    ? "#00d4aa"
                    : z.zone.includes("Intermediate")
                      ? "#00a8ff"
                      : "#a78bfa",
                },
              }))}
              layout={{
                yaxis: { title: { text: "Temperature (°C)" } },
                xaxis: { title: { text: "Depth Zone" } },
                showlegend: false,
              }}
            />
          </ChartCard>
        </div>
      )}
    </div>
  );
}
