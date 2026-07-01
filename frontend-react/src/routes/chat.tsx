import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState, useEffect } from "react";
import { Download, BarChart3, Trash2, Plus, MessageSquare, History } from "lucide-react";
import { useStore } from "@/store";
import { MessageList } from "@/components/chat/MessageList";
import { Composer } from "@/components/chat/Composer";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { GradientText } from "@/components/ui/GradientText";
import { useQuery } from "@tanstack/react-query";
import { getFloatDetail, getFloats, exportData, type ChatResponse } from "@/lib/api";
import { Shimmer } from "@/components/ui/Shimmer";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/chat")({
  head: () => ({
    meta: [
      { title: "Ocean Chat — SeaBorg" },
      {
        name: "description",
        content:
          "Ask the ocean: a RAG-powered chat over 694k+ ARGO float readings with live SQL and charts.",
      },
      { property: "og:title", content: "SeaBorg Ocean Chat" },
      {
        property: "og:description",
        content: "Plain-English queries over global ocean float data.",
      },
    ],
  }),
  component: ChatPage,
});

function ChatPage() {
  const messages = useStore((s) => s.messages);
  const sessions = useStore((s) => s.sessions);
  const activeSessionId = useStore((s) => s.activeSessionId);
  const createNewSession = useStore((s) => s.createNewSession);
  const switchSession = useStore((s) => s.switchSession);
  const deleteSession = useStore((s) => s.deleteSession);
  const selectedOcean = useStore((s) => s.selectedOcean);
  const setSelectedOcean = useStore((s) => s.setSelectedOcean);

  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [reportTitle, setReportTitle] = useState("");
  const [includeData, setIncludeData] = useState(false);
  const [includeSummary, setIncludeSummary] = useState(true);
  const [exportFormat, setExportFormat] = useState<"pdf" | "csv" | "both">("both");
  const [exporting, setExporting] = useState(false);

  const [plotHistory, setPlotHistory] = useState<
    Array<{
      id: number;
      messageId: string;
      chartType: string;
      data: ChatResponse["data"];
      query: string;
      timestamp: string;
      label: string;
      payload: ChatResponse;
    }>
  >([]);
  const [activeHistoryId, setActiveHistoryId] = useState<number | null>(null);
  const [historyCollapsed, setHistoryCollapsed] = useState(false);

  useEffect(() => {
    setPlotHistory([]);
    setActiveHistoryId(null);
  }, [activeSessionId]);

  useEffect(() => {
    if (exportModalOpen) {
      const today = new Date().toISOString().split("T")[0];
      setReportTitle(`SeaBorg Ocean Research Report — ${today}`);
    }
  }, [exportModalOpen]);

  const handleGenerateReport = async () => {
    if (messages.length === 0) return;
    setExporting(true);
    try {
      const history = [];
      for (let i = 0; i < messages.length; i++) {
        const m = messages[i];
        if (m.role === "user") {
          const aiResponse = messages[i + 1];
          if (aiResponse && aiResponse.role === "ai") {
            const payload = aiResponse.payload;
            history.push({
              query: m.text,
              response: payload.answer,
              chart_type: payload.chart_type,
              rows_retrieved: payload.data ? payload.data.length : 0,
              float_ids: payload.float_ids || [],
              status: payload.status || "ok",
              refusal_type: payload.refusal_type || null,
              closest_distance_km:
                payload.closest_distance_km !== undefined ? payload.closest_distance_km : null,
              data: payload.data || [],
              timestamp: m.ts,
            });
            i++;
          } else {
            history.push({
              query: m.text,
              response: "",
              chart_type: "none",
              rows_retrieved: 0,
              float_ids: [],
              status: "refused",
              refusal_type: "no_response",
              closest_distance_km: null,
              data: [],
              timestamp: m.ts,
            });
          }
        }
      }

      const body = {
        title: reportTitle,
        include_data: includeData,
        include_summary: includeSummary,
        format: exportFormat,
        ocean: selectedOcean,
        history,
      };

      const response = await fetch("http://localhost:8001/api/export_report", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error(`Export API error: ${response.statusText}`);
      }

      const blob = await response.blob();
      const contentDisposition = response.headers.get("Content-Disposition");
      const ext = exportFormat === "pdf" ? "pdf" : exportFormat === "csv" ? "csv" : "zip";
      let filename = `seaborg_report_${new Date().toISOString().split("T")[0]}.${ext}`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      setExportModalOpen(false);
    } catch (err) {
      console.error("Generate report failed:", err);
      alert(`Failed to export report: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setExporting(false);
    }
  };

  const lastAi = useMemo(() => [...messages].reverse().find((m) => m.role === "ai"), [messages]);

  const lastUserQuery = useMemo(() => {
    if (!lastAi) return "";
    const aiIndex = messages.findIndex((m) => m.id === lastAi.id);
    if (aiIndex > 0) {
      const prev = messages[aiIndex - 1];
      if (prev.role === "user") return prev.text;
    }
    return "";
  }, [messages, lastAi]);

  const activeChartType = useMemo(() => {
    if (!lastAi) return "none";
    const text = lastUserQuery.toLowerCase();

    // Check specific visualizer keywords to align with backend detect_chart_type logic
    if (
      text.includes("3d") ||
      text.includes("trajectory") ||
      text.includes("path") ||
      text.includes("route") ||
      text.includes("journey") ||
      text.includes("track")
    ) {
      return "3d_trajectory";
    }
    if (
      /\b(ts|t-s)\b/.test(text) ||
      text.includes("salinity vs") ||
      text.includes("temperature vs") ||
      text.includes("salinity and temperature") ||
      text.includes("compare temperature and salinity") ||
      text.includes("compare salinity and temperature")
    ) {
      return "ts_diagram";
    }
    if (
      text.includes("anomaly") ||
      text.includes("unusual") ||
      text.includes("deviation") ||
      text.includes("outlier") ||
      text.includes("abnormal")
    ) {
      return "anomaly";
    }
    if (
      text.includes("summarize") ||
      text.includes("overview") ||
      text.includes("stats for") ||
      text.includes("tell me about this region")
    ) {
      return "summary";
    }
    if (
      text.includes("compare") ||
      text.includes("vs") ||
      text.includes("versus") ||
      text.includes("difference between")
    ) {
      if (
        text.includes("vs") &&
        (text.includes("depth") || text.includes("profile") || text.includes("vertical"))
      ) {
        return "profile";
      }
      return "comparison";
    }

    return lastAi.payload.chart_type;
  }, [lastAi, lastUserQuery]);

  const activePlot = useMemo(() => {
    if (activeHistoryId !== null) {
      return plotHistory.find((p) => p.id === activeHistoryId) || null;
    }
    return null;
  }, [activeHistoryId, plotHistory]);

  useEffect(() => {
    if (lastAi && lastAi.role === "ai") {
      const payload = lastAi.payload;
      const chartType = activeChartType;
      const hasData = payload.data && payload.data.length > 0;

      if (chartType && chartType !== "none" && hasData) {
        const exists = plotHistory.some((p) => p.messageId === lastAi.id);
        if (!exists) {
          const newId = Date.now();
          const newEntry = {
            id: newId,
            messageId: lastAi.id,
            chartType: chartType,
            data: payload.data,
            query: lastUserQuery,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            label: `${chartType.toUpperCase().replace("_", " ")} — ${lastUserQuery.slice(0, 40)}${lastUserQuery.length > 40 ? "..." : ""}`,
            payload: payload,
          };
          setPlotHistory((prev) => [newEntry, ...prev]);
          setActiveHistoryId(newId);
        } else {
          const entry = plotHistory.find((p) => p.messageId === lastAi.id);
          if (entry) {
            setActiveHistoryId(entry.id);
          }
        }
      } else {
        setActiveHistoryId(null);
      }
    } else {
      setActiveHistoryId(null);
    }
  }, [lastAi?.id, activeChartType, lastUserQuery]);

  const handleClearHistory = () => {
    if (confirm("Clear all saved plots?")) {
      setPlotHistory([]);
      setActiveHistoryId(null);
    }
  };

  const exportCsv = async () => {
    const activePayload = activePlot ? activePlot.payload : lastAi?.payload;
    if (!activePayload) return;
    const floatIds = activePayload.float_ids ?? [];

    try {
      if (floatIds.length > 0) {
        // Download raw database CSV for these floats directly from backend
        await exportData(floatIds, "csv");
      } else {
        // Fallback: If no specific floats are linked, export the general float list
        const floats = await getFloats(100);
        const headers = ["id", "lat", "lng", "depth", "temp", "salinity", "last_reading"];
        const csvContent = [
          headers.join(","),
          ...floats.map((f) =>
            [f.id, f.lat, f.lng, f.depth, f.temp, f.salinity, f.last_reading]
              .map((val) => JSON.stringify(val ?? ""))
              .join(","),
          ),
        ].join("\n");

        const blob = new Blob([csvContent], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `seaborg-floats-${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error("Export failed", err);
    }
  };

  return (
    <div className="flex h-screen flex-col px-6 py-6 lg:px-10">
      <header className="mb-4 shrink-0 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            <GradientText>Ocean Chat</GradientText>
          </h1>
          <p className="text-xs text-muted-foreground">
            Retrieval-augmented generation over ARGO float datasets · Postgres + FAISS
          </p>
        </div>

        {/* Header Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* New Chat Button */}
          <button
            onClick={() => createNewSession()}
            className="flex items-center gap-1.5 rounded-lg border border-teal/20 bg-teal/5 px-3 py-1.5 text-xs font-semibold text-teal transition-all hover:bg-teal/10 hover:border-teal/30"
          >
            <Plus className="h-3.5 w-3.5" />
            New Chat
          </button>

          {/* History Hover Dropdown */}
          <div className="relative group">
            <button className="flex items-center gap-1.5 rounded-lg border border-[var(--glass-border)] bg-white/[0.02] px-3 py-1.5 text-xs text-muted-foreground transition-all hover:border-teal/40 hover:text-foreground">
              <History className="h-3.5 w-3.5" />
              Chat History
            </button>

            {/* Hover Menu Panel */}
            <div className="absolute right-0 top-full mt-2 w-[280px] glass rounded-xl border border-[var(--glass-border)] bg-black/90 p-2 shadow-2xl invisible opacity-0 translate-y-1 group-hover:visible group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-200 z-50">
              <div className="px-2 py-1.5 font-mono text-[9px] uppercase tracking-wider text-muted-foreground border-b border-[var(--glass-border)] mb-1 flex items-center justify-between">
                <span>Recent Chats</span>
                <span className="rounded bg-teal/10 px-1 py-0.5 text-teal text-[8px] font-semibold">
                  {sessions.length}
                </span>
              </div>
              <div className="max-h-[250px] overflow-y-auto space-y-0.5 pr-1">
                {sessions.length === 0 ? (
                  <div className="text-[10px] text-muted-foreground p-3 text-center">
                    No active conversations
                  </div>
                ) : (
                  sessions.map((s) => (
                    <div
                      key={s.id}
                      onClick={() => switchSession(s.id)}
                      className={cn(
                        "group/item flex items-center justify-between rounded-lg px-2 py-1.5 text-xs transition-colors cursor-pointer",
                        activeSessionId === s.id
                          ? "bg-white/[0.06] text-foreground font-medium border border-white/[0.05]"
                          : "text-muted-foreground hover:bg-white/[0.02] hover:text-foreground",
                      )}
                    >
                      <div className="flex items-center gap-2 truncate pr-2">
                        <MessageSquare className="h-3 w-3 shrink-0 text-teal/70" />
                        <span className="truncate">{s.title}</span>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteSession(s.id);
                        }}
                        className="opacity-0 group-hover/item:opacity-100 p-0.5 rounded text-muted-foreground hover:text-red-400 hover:bg-white/[0.06] transition-opacity"
                        aria-label="Delete chat"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Export Report Button */}
          <button
            onClick={() => setExportModalOpen(true)}
            disabled={messages.length === 0}
            className="flex items-center gap-1.5 rounded-lg border border-[var(--glass-border)] bg-white/[0.02] px-3 py-1.5 text-xs text-muted-foreground transition-all hover:border-teal/40 hover:text-foreground disabled:opacity-40 animate-in fade-in duration-300"
          >
            <Download className="h-3.5 w-3.5" />
            Export Report
          </button>
        </div>
      </header>

      {/* Main Layout containing Chat and Visualizer */}
      <div className="flex flex-1 min-h-0 gap-4">
        {/* Chat and visualizer grid */}
        <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Chat pane */}
          <div className="glass flex min-h-0 flex-col overflow-hidden">
            <MessageList />
            <Composer />
          </div>

          {/* Visualizer pane */}
          <div className="glass flex min-h-0 flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-[var(--glass-border)] px-5 py-3">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-ocean" />
                <h3 className="text-sm font-semibold">Live Visualizer</h3>
                {(activePlot || (lastAi && lastAi.role === "ai")) && (
                  <span className="ml-1 rounded-full border border-[var(--glass-border)] px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground animate-in fade-in duration-300">
                    {(activePlot ? activePlot.chartType : activeChartType).replace("_", " ")}
                  </span>
                )}
              </div>
              <button
                onClick={exportCsv}
                disabled={!lastAi && !activePlot}
                className="flex items-center gap-1.5 rounded-md border border-[var(--glass-border)] bg-white/[0.02] px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-teal/40 hover:text-foreground disabled:opacity-40"
              >
                <BarChart3 className="h-3.5 w-3.5" />
                Export CSV
              </button>
            </div>

            <div className="min-h-0 flex-1 overflow-hidden p-3">
              {activePlot ? (
                <Visualizer
                  payload={activePlot.payload}
                  userQuery={activePlot.query}
                  activeChartType={activePlot.chartType}
                />
              ) : lastAi && lastAi.role === "ai" && activeChartType !== "none" ? (
                <Visualizer
                  payload={lastAi.payload}
                  userQuery={lastUserQuery}
                  activeChartType={activeChartType}
                />
              ) : (
                <div className="grid h-full place-items-center text-center text-sm text-muted-foreground">
                  <div>
                    <BarChart3 className="mx-auto mb-2 h-8 w-8 opacity-40" />
                    <div>
                      {lastAi
                        ? "No visualization required for this query."
                        : "Charts appear here after your first question."}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Plot History panel at the bottom */}
            <div className="shrink-0 border-t border-[var(--glass-border)] bg-card transition-none">
              <div
                onClick={() => setHistoryCollapsed(!historyCollapsed)}
                className="flex cursor-pointer items-center justify-between px-5 py-2.5 hover:bg-white/[0.02] transition-colors"
              >
                <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
                  <History className="h-3.5 w-3.5 text-ocean" />
                  <span>Plot History</span>
                  <span className="rounded-full bg-ocean/10 border border-ocean/20 px-1.5 py-0.5 text-[10px] text-ocean font-mono">
                    {plotHistory.length}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  {plotHistory.length > 0 && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleClearHistory();
                      }}
                      className="text-[10px] text-red-400 hover:text-red-300 font-medium transition-colors"
                    >
                      Clear
                    </button>
                  )}
                  <span className="text-muted-foreground text-[10px]">
                    {historyCollapsed ? "Show" : "Hide"}
                  </span>
                </div>
              </div>

              {!historyCollapsed && (
                <div className="max-h-[160px] overflow-y-auto border-t border-[var(--glass-border)] p-2 flex flex-col gap-1.5 animate-in slide-in-from-bottom duration-200 bg-card transition-none">
                  {plotHistory.length === 0 ? (
                    <div className="py-6 text-center text-xs text-muted-foreground">
                      No saved plots in this session.
                    </div>
                  ) : (
                    plotHistory.map((item) => {
                      const isActive =
                        activeHistoryId === item.id ||
                        (!activeHistoryId && lastAi?.id === item.messageId);
                      return (
                        <div
                          key={item.id}
                          onClick={() => setActiveHistoryId(item.id)}
                          className={cn(
                            "flex cursor-pointer items-center justify-between rounded-lg border p-2 text-xs transition-all hover:bg-white/[0.02]",
                            isActive
                              ? "border-teal/40 bg-teal/5 text-foreground font-medium"
                              : "border-[var(--glass-border)] bg-transparent text-muted-foreground hover:text-foreground",
                          )}
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <span
                              className={cn(
                                "rounded-full border px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider shrink-0",
                                isActive
                                  ? "border-teal/30 bg-teal/10 text-teal"
                                  : "border-[var(--glass-border)] text-muted-foreground",
                              )}
                            >
                              {item.chartType.replace("_", " ")}
                            </span>
                            <span className="truncate">{item.query}</span>
                          </div>
                          <span className="shrink-0 text-[10px] text-muted-foreground opacity-80">
                            {item.timestamp}
                          </span>
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Export Options Modal */}
      {exportModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="w-full max-w-md border border-[var(--glass-border)] bg-card rounded-2xl p-6 shadow-2xl animate-in fade-in duration-200">
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2 text-foreground">
              <Download className="h-4 w-4 text-teal" />
              Export Chat Report
            </h3>

            <div className="space-y-4">
              {/* Report Title */}
              <div>
                <label className="block text-[10px] text-muted-foreground uppercase tracking-wider font-mono mb-1.5">
                  Report Title
                </label>
                <input
                  type="text"
                  value={reportTitle}
                  onChange={(e) => setReportTitle(e.target.value)}
                  className="w-full rounded-lg border border-border bg-background text-foreground px-3 py-2 text-xs outline-none focus:border-teal/40 transition-colors"
                />
              </div>

              {/* Include Summary Checkbox */}
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  id="include-summary"
                  checked={includeSummary}
                  onChange={(e) => setIncludeSummary(e.target.checked)}
                  className="mt-0.5 rounded border-border bg-transparent text-teal focus:ring-teal/30 focus:ring-offset-0 h-4 w-4"
                />
                <div>
                  <label
                    htmlFor="include-summary"
                    className="text-xs font-medium cursor-pointer text-foreground"
                  >
                    Include AI-generated chat summary
                  </label>
                  <p className="text-[10px] text-muted-foreground">
                    Generates a professional 150-250 word third-person academic summary.
                  </p>
                </div>
              </div>

              {/* Include ARGO rows Checkbox */}
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  id="include-data"
                  checked={includeData}
                  onChange={(e) => setIncludeData(e.target.checked)}
                  className="mt-0.5 rounded border-border bg-transparent text-teal focus:ring-teal/30 focus:ring-offset-0 h-4 w-4"
                />
                <div>
                  <label
                    htmlFor="include-data"
                    className="text-xs font-medium cursor-pointer text-foreground"
                  >
                    Include retrieved ARGO data rows
                  </label>
                  <p className="text-[10px] text-muted-foreground">
                    Includes a raw data appendix in the PDF and outputs a second CSV file.
                  </p>
                </div>
              </div>

              {/* Format Selector */}
              <div>
                <label className="block text-[10px] text-muted-foreground uppercase tracking-wider font-mono mb-1.5">
                  Export Format
                </label>
                <select
                  value={exportFormat}
                  onChange={(e) => setExportFormat(e.target.value as any)}
                  className="w-full rounded-lg border border-border bg-background text-foreground px-3 py-2 text-xs outline-none focus:border-teal/40 transition-colors"
                >
                  <option value="both">Both (PDF & CSV Zip)</option>
                  <option value="pdf">PDF Report</option>
                  <option value="csv">CSV Logs</option>
                </select>
              </div>
            </div>

            {/* Actions */}
            <div className="mt-6 flex justify-end gap-3 border-t border-[var(--glass-border)] pt-4">
              <button
                onClick={() => setExportModalOpen(false)}
                disabled={exporting}
                className="rounded-lg px-4 py-2 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerateReport}
                disabled={exporting}
                className="flex items-center gap-1.5 rounded-lg bg-teal px-4 py-2 text-xs font-semibold text-black hover:opacity-90 transition-colors disabled:opacity-50"
              >
                {exporting ? (
                  <>
                    <span className="h-3.5 w-3.5 animate-spin rounded-full border border-black border-t-transparent" />
                    Generating...
                  </>
                ) : (
                  "Generate Report"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SparseDataFallback({ data, variable }: { data: any[]; variable: string }) {
  const metricLabel =
    variable === "salinity" ? "Salinity" : variable === "oxygen" ? "Oxygen" : "Temperature";

  return (
    <div className="flex h-full flex-col justify-center p-4">
      <div className="mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider text-left">
        ⚠️ Sparse Readings ({data.length} records found)
      </div>
      <div className="overflow-hidden rounded-xl border border-[var(--glass-border)] bg-black/40">
        <table className="w-full border-collapse text-left text-xs">
          <thead>
            <tr className="border-b border-[var(--glass-border)] bg-white/[0.02] text-muted-foreground font-semibold">
              <th className="p-2.5">Float ID</th>
              <th className="p-2.5">Date</th>
              <th className="p-2.5">Depth</th>
              <th className="p-2.5 text-teal">{metricLabel}</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d, idx) => {
              const val =
                variable === "salinity" ? d.salinity : variable === "oxygen" ? d.oxygen : d.temp;
              const suffix =
                variable === "salinity" ? " PSU" : variable === "oxygen" ? " µmol/kg" : "°C";
              return (
                <tr
                  key={idx}
                  className="border-b border-white/[0.02] last:border-0 hover:bg-white/[0.01]"
                >
                  <td className="p-2.5 font-mono text-[11px] font-semibold text-ocean">
                    {d.id || d.float_id || "N/A"}
                  </td>
                  <td className="p-2.5 font-mono text-[11px] text-muted-foreground">
                    {d.date || "N/A"}
                  </td>
                  <td className="p-2.5 font-mono text-[11px]">{d.depth ?? d.depth_m}m</td>
                  <td className="p-2.5 font-mono text-[11px] text-teal font-semibold">
                    {val !== undefined && val !== null ? `${val.toFixed(2)}${suffix}` : "N/A"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Visualizer({
  payload,
  userQuery,
  activeChartType,
}: {
  payload: any;
  userQuery: string;
  activeChartType: string;
}) {
  const { float_ids = [] } = payload;
  const floatId = float_ids[0];

  // Map comparison chart types based on query keyword hints
  const resolvedChartType = useMemo(() => {
    if (activeChartType === "comparison") {
      const q = userQuery.toLowerCase();
      if (q.includes("profile") || q.includes("depth") || q.includes("vertical")) {
        return "profile";
      }
      if (q.includes("trend") || q.includes("time") || q.includes("change")) {
        return "timeseries";
      }
    }
    return activeChartType;
  }, [activeChartType, userQuery]);

  // Fetch detail if profile, timeseries, ts_diagram or 3d_trajectory and payload.data is empty
  const { data: detailData = [], isLoading: isDetailLoading } = useQuery({
    queryKey: ["float-detail", floatId],
    queryFn: () => getFloatDetail(floatId),
    enabled:
      !payload.data?.length &&
      !!floatId &&
      (resolvedChartType === "profile" ||
        resolvedChartType === "timeseries" ||
        resolvedChartType === "ts_diagram" ||
        resolvedChartType === "3d_trajectory"),
  });

  // Fetch all floats if map
  const { data: allFloats = [], isLoading: isFloatsLoading } = useQuery({
    queryKey: ["floats", 100],
    queryFn: () => getFloats(100),
    enabled: !payload.data?.length && resolvedChartType === "map",
  });

  // Scientific variable detection based on SQL query and User query keywords
  const variable = useMemo(() => {
    const sql = (payload.sql_used ?? "").toLowerCase();
    const text = userQuery.toLowerCase();
    if (
      sql.includes("salinity") ||
      text.includes("salinity") ||
      text.includes("salt") ||
      text.includes("psu")
    ) {
      return "salinity";
    }
    if (sql.includes("oxygen") || text.includes("oxygen") || text.includes("o2")) {
      return "oxygen";
    }
    return "temperature";
  }, [payload.sql_used, userQuery]);

  // Geographic region detection for auto-zooming the maps
  const region = useMemo(() => {
    const text = userQuery.toLowerCase();
    if (text.includes("indian ocean") || text.includes("indian")) return "indian ocean";
    if (text.includes("pacific ocean") || text.includes("pacific")) return "pacific ocean";
    if (text.includes("atlantic ocean") || text.includes("atlantic")) return "atlantic ocean";
    if (text.includes("arabian sea") || text.includes("arabian")) return "arabian sea";
    if (text.includes("bay of bengal") || text.includes("bengal")) return "bay of bengal";
    if (text.includes("south china sea") || text.includes("china sea")) return "south china sea";
    if (text.includes("mediterranean sea") || text.includes("mediterranean"))
      return "mediterranean sea";
    return null;
  }, [userQuery]);

  // Unified active data extraction
  const activeData =
    payload.data?.length > 0
      ? payload.data.map((d: any) => ({
          temp: d.temp ?? d.temp_c ?? 0,
          depth: d.depth ?? d.depth_m ?? 0,
          salinity: d.salinity ?? 34.5,
          oxygen: d.oxygen ?? 0,
          lat: d.lat ?? d.latitude ?? 0,
          lng: d.lng ?? d.longitude ?? 0,
          date: d.date ? d.date.slice(0, 10) : "",
          id: String(d.id ?? d.float_id ?? ""),
          float_id: String(d.float_id ?? d.id ?? ""),
        }))
      : detailData.length > 0
        ? detailData.map((d: any) => ({
            temp: d.temp_c ?? 0,
            depth: d.depth_m ?? 0,
            salinity: d.salinity ?? 34.5,
            oxygen: d.oxygen ?? 0,
            lat: d.latitude ?? 0,
            lng: d.longitude ?? 0,
            date: d.date ? d.date.slice(0, 10) : "",
            id: String(floatId),
            float_id: String(floatId),
          }))
        : [];

  // Set unique float IDs
  const uniqueFloatIds = useMemo(() => {
    const ids = activeData.map((d: any) => String(d.float_id || d.id)).filter(Boolean);
    return Array.from(new Set(ids));
  }, [activeData]);

  // Sparse data fallback table trigger (for charts with lines/markers)
  if (
    activeData.length > 0 &&
    activeData.length < 3 &&
    resolvedChartType !== "map" &&
    resolvedChartType !== "summary"
  ) {
    return <SparseDataFallback data={activeData} variable={variable} />;
  }

  // 1. COMPARISON Grouped Bar Chart (default comparison)
  if (resolvedChartType === "comparison") {
    const metricLabel =
      variable === "salinity"
        ? "Salinity (PSU)"
        : variable === "oxygen"
          ? "Oxygen (µmol/kg)"
          : "Temperature (°C)";
    const colors = ["#00d4aa", "#00a8ff", "#a78bfa", "#f59e0b", "#ff5577"];

    const traces = uniqueFloatIds
      .map((fid, idx) => {
        const floatData = activeData.filter((d: any) => String(d.float_id) === fid);
        if (floatData.length === 0) return null;
        const avg =
          floatData.reduce(
            (sum: number, d: any) =>
              sum +
              (variable === "salinity" ? d.salinity : variable === "oxygen" ? d.oxygen : d.temp),
            0,
          ) / floatData.length;

        return {
          type: "bar",
          x: [`Float ${fid}`],
          y: [avg],
          name: `Float ${fid}`,
          marker: { color: colors[idx % colors.length] },
        };
      })
      .filter(Boolean);

    if (traces.length === 0) {
      return (
        <div className="grid h-full place-items-center text-center text-xs text-muted-foreground">
          No comparison data available.
        </div>
      );
    }

    return (
      <PlotlyChart
        data={traces}
        layout={{
          title: { text: `Average ${metricLabel} Comparison`, font: { color: "#cbd0dc" } },
          xaxis: { title: { text: "Float Series" } },
          yaxis: { title: { text: metricLabel } },
          barmode: "group",
        }}
      />
    );
  }

  // 2. ANOMALY Detection Chart
  if (resolvedChartType === "anomaly") {
    const metricLabel =
      variable === "salinity" ? "Salinity" : variable === "oxygen" ? "Oxygen" : "Temperature";
    const values = activeData.map(
      (d: any) =>
        (variable === "salinity"
          ? d.salinity
          : variable === "oxygen"
            ? d.oxygen
            : d.temp) as number,
    );
    const n = values.length;
    if (n === 0) {
      return (
        <div className="grid h-full place-items-center text-center text-xs text-muted-foreground">
          No data available for anomaly analysis.
        </div>
      );
    }

    const mean = values.reduce((sum, v) => sum + v, 0) / n;
    const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / n;
    const stdDev = Math.sqrt(variance) || 1.0;

    const upperThreshold = mean + 2 * stdDev;
    const lowerThreshold = mean - 2 * stdDev;

    const normalPoints = activeData.filter((d: any) => {
      const val = variable === "salinity" ? d.salinity : variable === "oxygen" ? d.oxygen : d.temp;
      return val >= lowerThreshold && val <= upperThreshold;
    });

    const anomalyPoints = activeData.filter((d: any) => {
      const val = variable === "salinity" ? d.salinity : variable === "oxygen" ? d.oxygen : d.temp;
      return val < lowerThreshold || val > upperThreshold;
    });

    const dates = activeData.map((d: any) => d.date);

    return (
      <PlotlyChart
        data={[
          {
            type: "scatter",
            mode: "lines",
            name: "Mean Baseline",
            x: dates,
            y: dates.map(() => mean),
            line: { color: "rgba(255,255,255,0.4)", width: 1.5, dash: "dash" },
          },
          {
            type: "scatter",
            mode: "lines",
            name: "+2 Std Dev",
            x: dates,
            y: dates.map(() => upperThreshold),
            line: { color: "rgba(255, 85, 119, 0.3)", width: 1, dash: "dot" },
          },
          {
            type: "scatter",
            mode: "lines",
            name: "-2 Std Dev",
            x: dates,
            y: dates.map(() => lowerThreshold),
            line: { color: "rgba(255, 85, 119, 0.3)", width: 1, dash: "dot" },
          },
          {
            type: "scatter",
            mode: "markers",
            name: "Normal Readings",
            x: normalPoints.map((d: any) => d.date),
            y: normalPoints.map((d: any) =>
              variable === "salinity" ? d.salinity : variable === "oxygen" ? d.oxygen : d.temp,
            ),
            marker: { color: "#00d4aa", size: 6, opacity: 0.7 },
          },
          {
            type: "scatter",
            mode: "markers+text",
            name: "Anomalies (>2 SD)",
            x: anomalyPoints.map((d: any) => d.date),
            y: anomalyPoints.map((d: any) =>
              variable === "salinity" ? d.salinity : variable === "oxygen" ? d.oxygen : d.temp,
            ),
            text: anomalyPoints.map(() => "⚠️ Outlier"),
            textposition: "top center",
            marker: { color: "#ff5577", size: 10, line: { color: "#ffffff", width: 1 } },
          },
        ]}
        layout={{
          title: { text: `${metricLabel} Anomaly Analysis`, font: { color: "#cbd0dc" } },
          xaxis: { title: { text: "Date" } },
          yaxis: {
            title: {
              text:
                variable === "salinity"
                  ? "Salinity (PSU)"
                  : variable === "oxygen"
                    ? "Oxygen (µmol/kg)"
                    : "Temperature (°C)",
            },
          },
        }}
      />
    );
  }

  // 3. REGIONAL SUMMARY Card Grid
  if (resolvedChartType === "summary") {
    const temps = activeData.map((d: any) => d.temp).filter((v) => v !== undefined && !isNaN(v));
    const sals = activeData.map((d: any) => d.salinity).filter((v) => v !== undefined && !isNaN(v));
    const depths = activeData.map((d: any) => d.depth).filter((v) => v !== undefined && !isNaN(v));
    const dates = activeData.map((d: any) => d.date).filter(Boolean);

    const stats = {
      temp: {
        min: temps.length ? Math.min(...temps) : 0,
        max: temps.length ? Math.max(...temps) : 0,
        mean: temps.length ? temps.reduce((a, b) => a + b, 0) / temps.length : 0,
      },
      salinity: {
        min: sals.length ? Math.min(...sals) : 0,
        max: sals.length ? Math.max(...sals) : 0,
        mean: sals.length ? sals.reduce((a, b) => a + b, 0) / sals.length : 0,
      },
      depth: {
        min: depths.length ? Math.min(...depths) : 0,
        max: depths.length ? Math.max(...depths) : 0,
        mean: depths.length ? depths.reduce((a, b) => a + b, 0) / depths.length : 0,
      },
      count: activeData.length,
      dateRange: dates.length ? `${dates.sort()[0]} to ${dates.sort()[dates.length - 1]}` : "N/A",
    };

    if (stats.count === 0) {
      return (
        <div className="grid h-full place-items-center text-center text-xs text-muted-foreground font-mono">
          No stats available for this region.
        </div>
      );
    }

    return (
      <div className="flex h-full flex-col justify-center p-4">
        <div className="mb-3 font-mono text-[10px] uppercase tracking-wider text-muted-foreground text-left">
          📊 Regional Statistics Overview (Based on {stats.count} readings)
        </div>
        <div className="grid grid-cols-3 gap-3 mb-3">
          {/* Temp Card */}
          <div className="rounded-xl border border-[var(--glass-border)] bg-white/[0.02] p-3 text-left">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Temperature
            </div>
            <div className="mt-1 font-mono text-lg font-bold text-teal">
              {stats.temp.mean.toFixed(2)}°C
            </div>
            <div className="mt-1 flex justify-between font-mono text-[9px] text-muted-foreground">
              <span>Min: {stats.temp.min.toFixed(1)}°</span>
              <span>Max: {stats.temp.max.toFixed(1)}°</span>
            </div>
          </div>

          {/* Salinity Card */}
          <div className="rounded-xl border border-[var(--glass-border)] bg-white/[0.02] p-3 text-left">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Salinity
            </div>
            <div className="mt-1 font-mono text-lg font-bold text-teal">
              {stats.salinity.mean.toFixed(2)} PSU
            </div>
            <div className="mt-1 flex justify-between font-mono text-[9px] text-muted-foreground">
              <span>Min: {stats.salinity.min.toFixed(1)}</span>
              <span>Max: {stats.salinity.max.toFixed(1)}</span>
            </div>
          </div>

          {/* Depth Card */}
          <div className="rounded-xl border border-[var(--glass-border)] bg-white/[0.02] p-3 text-left">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Depth</div>
            <div className="mt-1 font-mono text-lg font-bold text-teal">
              {stats.depth.mean.toFixed(0)}m
            </div>
            <div className="mt-1 flex justify-between font-mono text-[9px] text-muted-foreground">
              <span>Min: {stats.depth.min.toFixed(0)}m</span>
              <span>Max: {stats.depth.max.toFixed(0)}m</span>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-[var(--glass-border)] bg-white/[0.01] px-3 py-2 flex justify-between items-center text-[10px] text-muted-foreground font-mono">
          <span>📅 Period: {stats.dateRange}</span>
          <span className="rounded bg-teal/10 px-1.5 py-0.5 text-teal font-semibold">
            Total readings: {stats.count}
          </span>
        </div>
      </div>
    );
  }

  // 4. PROFILE, TIMESERIES, TS DIAGRAM, 3D TRAJECTORY
  if (
    resolvedChartType === "profile" ||
    resolvedChartType === "timeseries" ||
    resolvedChartType === "ts_diagram" ||
    resolvedChartType === "3d_trajectory"
  ) {
    if (!floatId && !payload.data?.length) {
      return (
        <div className="grid h-full place-items-center text-center text-xs text-muted-foreground font-mono">
          No active float associated with this query.
        </div>
      );
    }
    if (isDetailLoading && !payload.data?.length) {
      return (
        <div className="p-6 h-full flex flex-col justify-center">
          <Shimmer className="h-44 w-full" />
        </div>
      );
    }

    // Advanced Oceanography: TS (Temperature-Salinity) Diagram
    if (resolvedChartType === "ts_diagram") {
      const colors = ["#00d4aa", "#00a8ff", "#a78bfa", "#f59e0b", "#ff5577"];
      const traces = uniqueFloatIds.map((fid, idx) => {
        const floatData = activeData.filter((d: any) => String(d.float_id) === fid);
        return {
          type: "scatter",
          mode: "markers",
          name: `Float ${fid}`,
          x: floatData.map((d: any) => d.salinity as number),
          y: floatData.map((d: any) => d.temp as number),
          marker: {
            size: 8,
            color:
              uniqueFloatIds.length > 1
                ? colors[idx % colors.length]
                : floatData.map((d: any) => d.depth as number),
            colorscale: uniqueFloatIds.length > 1 ? undefined : "Viridis",
            reversescale: true,
            colorbar:
              uniqueFloatIds.length > 1
                ? undefined
                : {
                    title: { text: "Depth (m)", font: { color: "#cbd0dc" } },
                    tickfont: { color: "#8a8fa3" },
                    outlinewidth: 0,
                    thickness: 10,
                  },
            line: { color: "rgba(255,255,255,0.15)", width: 0.5 },
          },
          text: floatData.map((d: any) => `Depth: ${d.depth}m · Date: ${d.date}`),
          hovertemplate: "Salinity: %{x} PSU<br>Temp: %{y}°C<br>%{text}<extra></extra>",
        };
      });

      return (
        <PlotlyChart
          data={traces}
          layout={{
            xaxis: { title: { text: "Salinity (PSU)" } },
            yaxis: { title: { text: "Temperature (°C)" } },
            showlegend: uniqueFloatIds.length > 1,
          }}
        />
      );
    }

    // Advanced Trajectory: 3D trajectory plot in space-depth coordinates
    if (resolvedChartType === "3d_trajectory") {
      const colors = ["#00a8ff", "#00d4aa", "#a78bfa", "#f59e0b", "#ff5577"];
      const traces = uniqueFloatIds.map((fid, idx) => {
        const floatData = activeData.filter((d: any) => String(d.float_id) === fid);
        return {
          type: "scatter3d",
          mode: "lines+markers",
          name: `Float ${fid}`,
          x: floatData.map((d: any) => d.lng as number),
          y: floatData.map((d: any) => d.lat as number),
          z: floatData.map((d: any) => d.depth as number),
          line: { color: colors[idx % colors.length], width: 3 },
          marker: {
            size: 4,
            color: colors[idx % colors.length],
          },
          text: floatData.map((d: any) => `${d.date}<br>${d.temp}°C · Sal: ${d.salinity} PSU`),
          hovertemplate: "Lng: %{x}<br>Lat: %{y}<br>Depth: %{z}m<br>%{text}<extra></extra>",
        };
      });

      return (
        <PlotlyChart
          data={traces}
          layout={{
            scene: {
              xaxis: { title: { text: "Longitude" }, gridcolor: "rgba(255,255,255,0.06)" },
              yaxis: { title: { text: "Latitude" }, gridcolor: "rgba(255,255,255,0.06)" },
              zaxis: {
                title: { text: "Depth (m)" },
                autorange: "reversed",
                gridcolor: "rgba(255,255,255,0.06)",
              },
              camera: { eye: { x: 1.5, y: 1.5, z: 1.5 } },
            },
            margin: { l: 0, r: 0, t: 0, b: 0 },
            showlegend: uniqueFloatIds.length > 1,
          }}
        />
      );
    }

    // Select profile data metrics based on variable
    let xTitle = "Temperature (°C)";
    if (variable === "salinity") {
      xTitle = "Salinity (PSU)";
    } else if (variable === "oxygen") {
      xTitle = "Oxygen Concentration (µmol/kg)";
    }

    if (resolvedChartType === "profile") {
      const colors = ["#00d4aa", "#00a8ff", "#a78bfa", "#f59e0b", "#ff5577"];
      const traces = uniqueFloatIds.map((fid, idx) => {
        const floatData = activeData.filter((d: any) => String(d.float_id) === fid);
        let xData: number[];
        if (variable === "salinity") {
          xData = floatData.map((d: any) => d.salinity as number);
        } else if (variable === "oxygen") {
          xData = floatData.map((d: any) => d.oxygen as number);
        } else {
          xData = floatData.map((d: any) => d.temp as number);
        }

        return {
          type: "scatter",
          mode: "lines+markers",
          name: `Float ${fid}`,
          x: xData,
          y: floatData.map((d: any) => d.depth as number),
          line: { color: colors[idx % colors.length], width: 2 },
          marker: { color: colors[(idx + 1) % colors.length], size: 6 },
          hovertemplate: `%{y} m · %{x} ${variable === "salinity" ? "PSU" : variable === "oxygen" ? "µmol/kg" : "°C"}<extra></extra>`,
        };
      });

      return (
        <PlotlyChart
          data={traces}
          layout={{
            xaxis: { title: { text: xTitle } },
            yaxis: { title: { text: "Depth (m)" }, autorange: "reversed" },
            showlegend: uniqueFloatIds.length > 1,
          }}
        />
      );
    }

    // Timeseries Plot configs
    let yTitle = "Avg Temp (°C)";
    if (variable === "salinity") {
      yTitle = "Salinity (PSU)";
    } else if (variable === "oxygen") {
      yTitle = "Oxygen Concentration (µmol/kg)";
    }

    const colors = ["#00a8ff", "#00d4aa", "#a78bfa", "#f59e0b", "#ff5577"];
    const traces = uniqueFloatIds.map((fid, idx) => {
      const floatData = activeData.filter((d: any) => String(d.float_id) === fid);
      let yData: number[];
      if (variable === "salinity") {
        yData = floatData.map((d: any) => d.salinity as number);
      } else if (variable === "oxygen") {
        yData = floatData.map((d: any) => d.oxygen as number);
      } else {
        yData = floatData.map((d: any) => d.temp as number);
      }

      return {
        type: "scatter",
        mode: "lines+markers",
        name: `Float ${fid}`,
        x: floatData.map((d: any) => d.date as string),
        y: yData,
        line: { color: colors[idx % colors.length], width: 2, shape: "spline" },
        marker: { color: colors[(idx + 1) % colors.length], size: 5 },
        fill: uniqueFloatIds.length > 1 ? undefined : "tozeroy",
        fillcolor: uniqueFloatIds.length > 1 ? undefined : "rgba(0,168,255,0.08)",
        hovertemplate: `%{x} · %{y} ${variable === "salinity" ? "PSU" : variable === "oxygen" ? "µmol/kg" : "°C"}<extra></extra>`,
      };
    });

    return (
      <PlotlyChart
        data={traces}
        layout={{
          xaxis: { title: { text: "Date" } },
          yaxis: { title: { text: yTitle } },
          showlegend: uniqueFloatIds.length > 1,
        }}
      />
    );
  }

  // 5. GEOGRAPHIC MAP
  if (resolvedChartType === "map") {
    if (isFloatsLoading && !payload.data?.length) {
      return (
        <div className="p-6 h-full flex flex-col justify-center">
          <Shimmer className="h-44 w-full" />
        </div>
      );
    }

    const mapFloats =
      float_ids.length > 0 ? allFloats.filter((f: any) => float_ids.includes(f.id)) : allFloats;

    const activeData =
      payload.data?.length > 0
        ? payload.data.map((d: any) => ({
            id: String(d.float_id ?? d.id),
            lat: d.lat ?? d.latitude,
            lng: d.lng ?? d.longitude,
            temp: d.temp ?? d.temp_c,
            salinity: d.salinity ?? 34.5,
            oxygen: d.oxygen ?? 0,
          }))
        : mapFloats.length > 0
          ? mapFloats
          : [];

    // Group markers by float ID for mapping
    const mapUniqueIds = Array.from(new Set(activeData.map((d: any) => String(d.id))));
    const colors = ["#00d4aa", "#00a8ff", "#a78bfa", "#f59e0b", "#ff5577"];

    // Select color values for markers if single float map
    let colorTitle = "°C";
    let colorScale: any = [
      [0, "#00d4aa"],
      [1, "#00a8ff"],
    ];

    if (variable === "salinity") {
      colorTitle = "PSU";
      colorScale = [
        [0, "#00a8ff"],
        [1, "#a78bfa"],
      ];
    } else if (variable === "oxygen") {
      colorTitle = "O₂";
      colorScale = [
        [0, "#a78bfa"],
        [1, "#f59e0b"],
      ];
    }

    const mapTraces = mapUniqueIds.map((fid, idx) => {
      const floatData = activeData.filter((d: any) => String(d.id) === fid);
      const col =
        variable === "salinity"
          ? floatData.map((d: any) => d.salinity as number)
          : variable === "oxygen"
            ? floatData.map((d: any) => d.oxygen as number)
            : floatData.map((d: any) => d.temp as number);

      return {
        type: "scattergeo",
        mode: "markers",
        name: `Float ${fid}`,
        lat: floatData.map((d: any) => d.lat as number),
        lon: floatData.map((d: any) => d.lng as number),
        text: floatData.map((d: any) => `${fid} · ${d.temp}°C · Sal: ${d.salinity}`),
        marker: {
          size: activeData.length < 20 ? 12 : activeData.length < 100 ? 9 : 7,
          color: mapUniqueIds.length > 1 ? colors[idx % colors.length] : col,
          colorscale: mapUniqueIds.length > 1 ? undefined : colorScale,
          opacity: 0.85,
          line: { color: "rgba(255,255,255,0.2)", width: 0.5 },
          colorbar:
            mapUniqueIds.length > 1
              ? undefined
              : {
                  title: { text: colorTitle, font: { color: "#cbd0dc" } },
                  tickfont: { color: "#8a8fa3" },
                  outlinewidth: 0,
                  thickness: 10,
                },
        },
        hovertemplate: "%{text}<extra></extra>",
      };
    });

    // Dynamic region bounds zoom settings
    const geoLayout: any = {
      projection: { type: "natural earth" },
      showland: true,
      landcolor: "#13131c",
      showocean: true,
      oceancolor: "#07070d",
      showcoastlines: true,
      coastlinecolor: "rgba(0,212,170,0.25)",
      showcountries: true,
      countrycolor: "rgba(255,255,255,0.05)",
      showframe: false,
    };

    // Calculate proximity map focus bounding box
    const distances =
      payload.data?.map((d: any) => d.distance_km).filter((d: any) => d !== undefined) ?? [];
    const hasProximity = distances.length > 0;

    if (hasProximity && activeData.length > 0) {
      const avgLat = activeData.reduce((sum: number, d: any) => sum + d.lat, 0) / activeData.length;
      const avgLng = activeData.reduce((sum: number, d: any) => sum + d.lng, 0) / activeData.length;
      geoLayout.projection = { type: "mercator" };
      geoLayout.lonaxis = { showgrid: true, range: [avgLng - 15, avgLng + 15] };
      geoLayout.lataxis = { showgrid: true, range: [avgLat - 15, avgLat + 15] };
    } else if (region === "indian ocean") {
      geoLayout.lonaxis = { showgrid: true, range: [10, 130] };
      geoLayout.lataxis = { showgrid: true, range: [-40, 40] };
    } else if (region === "pacific ocean") {
      geoLayout.lonaxis = { showgrid: true, range: [110, 290] };
      geoLayout.lataxis = { showgrid: true, range: [-40, 40] };
    } else if (region === "atlantic ocean") {
      geoLayout.lonaxis = { showgrid: true, range: [-80, 30] };
      geoLayout.lataxis = { showgrid: true, range: [-40, 40] };
    } else if (region === "arabian sea") {
      geoLayout.lonaxis = { showgrid: true, range: [45, 80] };
      geoLayout.lataxis = { showgrid: true, range: [0, 30] };
    } else if (region === "bay of bengal") {
      geoLayout.lonaxis = { showgrid: true, range: [75, 105] };
      geoLayout.lataxis = { showgrid: true, range: [0, 30] };
    } else if (region === "south china sea") {
      geoLayout.lonaxis = { showgrid: true, range: [95, 125] };
      geoLayout.lataxis = { showgrid: true, range: [-5, 30] };
    } else if (region === "mediterranean sea") {
      geoLayout.lonaxis = { showgrid: true, range: [-10, 40] };
      geoLayout.lataxis = { showgrid: true, range: [25, 50] };
    }

    return (
      <PlotlyChart
        data={mapTraces}
        layout={{
          margin: { l: 0, r: 0, t: 0, b: 0 },
          geo: geoLayout,
          showlegend: mapUniqueIds.length > 1,
        }}
      />
    );
  }

  return null;
}
