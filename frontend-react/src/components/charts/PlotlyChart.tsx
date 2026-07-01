import { useEffect, useState, useMemo, type ComponentType } from "react";
import { useStore } from "@/store";

type PlotProps = {
  data: unknown[];
  layout?: Record<string, unknown>;
  config?: Record<string, unknown>;
  style?: React.CSSProperties;
  className?: string;
  useResizeHandler?: boolean;
};

export function getThemeLayout(theme: "dark" | "light"): Record<string, unknown> {
  const isLight = theme === "light";
  return {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: {
      family: "Outfit, Inter, sans-serif",
      color: isLight ? "#0f172a" : "#cbd0dc",
      size: 12,
    },
    colorway: isLight
      ? ["#00b490", "#0284c7", "#8b5cf6", "#f59e0b", "#ef4444"]
      : ["#00d4aa", "#00a8ff", "#a78bfa", "#f59e0b", "#ff5577"],
    margin: { l: 50, r: 20, t: 30, b: 40 },
    xaxis: {
      gridcolor: isLight ? "rgba(15,23,42,0.06)" : "rgba(255,255,255,0.06)",
      zerolinecolor: isLight ? "rgba(15,23,42,0.10)" : "rgba(255,255,255,0.10)",
      linecolor: isLight ? "rgba(15,23,42,0.10)" : "rgba(255,255,255,0.10)",
      tickfont: { color: isLight ? "#64748b" : "#8a8fa3" },
      spikecolor: isLight ? "#1a1a2e" : "#ffffff",
      spikethickness: 1,
      spikedash: "dot",
      spikemode: "across",
      spikesnap: "cursor",
    },
    yaxis: {
      gridcolor: isLight ? "rgba(15,23,42,0.06)" : "rgba(255,255,255,0.06)",
      zerolinecolor: isLight ? "rgba(15,23,42,0.10)" : "rgba(255,255,255,0.10)",
      linecolor: isLight ? "rgba(15,23,42,0.10)" : "rgba(255,255,255,0.10)",
      tickfont: { color: isLight ? "#64748b" : "#8a8fa3" },
      spikecolor: isLight ? "#1a1a2e" : "#ffffff",
      spikethickness: 1,
      spikedash: "dot",
      spikemode: "across",
      spikesnap: "cursor",
    },
    legend: { font: { color: isLight ? "#0f172a" : "#cbd0dc" } },
    hoverlabel: {
      bgcolor: isLight ? "#1e293b" : "#0d0d14",
      bordercolor: isLight ? "#00b490" : "#00d4aa",
      font: { color: "#ffffff", family: "JetBrains Mono, monospace" },
    },
    modebar: isLight
      ? {
          bgcolor: "rgba(240, 240, 245, 0.9)",
          color: "#555570",
          activecolor: "#0088cc",
        }
      : {
          bgcolor: "rgba(20, 20, 30, 0.9)",
          color: "#8888aa",
          activecolor: "#00d4ff",
        },
    geo: {
      bgcolor: "rgba(0,0,0,0)",
      showland: true,
      landcolor: isLight ? "#f8fafc" : "#13131c",
      showocean: true,
      oceancolor: isLight ? "#e0f2fe" : "#07070d",
      showcoastlines: true,
      coastlinecolor: isLight ? "rgba(0,180,144,0.25)" : "rgba(0,212,170,0.25)",
      showcountries: true,
      countrycolor: isLight ? "rgba(15,23,42,0.05)" : "rgba(255,255,255,0.05)",
      showframe: false,
      projection: { type: "natural earth" },
    },
  };
}

export const baseConfig = {
  displayModeBar: "hover",
  displaylogo: false,
  responsive: true,
};

export function PlotlyChart(props: PlotProps) {
  const theme = useStore((s) => s.theme);
  const [Plot, setPlot] = useState<ComponentType<PlotProps> | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      const [{ default: createPlotlyComponent }, Plotly] = await Promise.all([
        import("react-plotly.js/factory"),
        import("plotly.js-dist-min"),
      ]);
      const Component = createPlotlyComponent(Plotly.default ?? Plotly);
      if (mounted) setPlot(() => Component as ComponentType<PlotProps>);
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const themeLayout = getThemeLayout(theme);
  const isLight = theme === "light";
  const mergedLayout = {
    ...themeLayout,
    ...props.layout,
    xaxis: {
      ...(themeLayout.xaxis as Record<string, unknown>),
      ...(props.layout?.xaxis as Record<string, unknown>),
      spikecolor: isLight ? "#1a1a2e" : "#ffffff",
      spikethickness: 1,
      spikedash: "dot",
      spikemode: "across",
      spikesnap: "cursor",
    },
    yaxis: {
      ...(themeLayout.yaxis as Record<string, unknown>),
      ...(props.layout?.yaxis as Record<string, unknown>),
      spikecolor: isLight ? "#1a1a2e" : "#ffffff",
      spikethickness: 1,
      spikedash: "dot",
      spikemode: "across",
      spikesnap: "cursor",
    },
    geo: {
      ...(themeLayout.geo as Record<string, unknown>),
      ...(props.layout?.geo as Record<string, unknown>),
    },
    uirevision: theme,
  };

  const safeLayout = useMemo(() => {
    return JSON.parse(JSON.stringify(mergedLayout));
  }, [theme, props.layout, props.data]);

  const revision = useMemo(() => {
    return Date.now();
  }, [theme, props.data]);

  if (!Plot) {
    return (
      <div
        className="h-full w-full rounded-md"
        style={{
          background:
            "linear-gradient(90deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 100%)",
          backgroundSize: "800px 100%",
          animation: "shimmer 1.6s linear infinite",
        }}
      />
    );
  }

  return (
    <Plot
      {...props}
      layout={safeLayout}
      config={{ ...baseConfig, ...(props.config ?? {}) }}
      revision={revision}
      useResizeHandler
      style={{ width: "100%", height: "100%", ...(props.style ?? {}) }}
    />
  );
}
