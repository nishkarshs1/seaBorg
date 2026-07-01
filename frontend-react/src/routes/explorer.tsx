import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, useEffect } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Filter,
  MapPin,
  Radio,
  Plus,
  Trash2,
  Edit2,
  SlidersHorizontal,
  Save,
  X,
} from "lucide-react";
import { getFloats, getHealth } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { GradientText } from "@/components/ui/GradientText";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { Shimmer } from "@/components/ui/Shimmer";
import { cn } from "@/lib/utils";
import { useStore, type FilterRule, type ExplorerFilter } from "@/store";

export const Route = createFileRoute("/explorer")({
  head: () => ({
    meta: [
      { title: "Data Explorer — SeaBorg" },
      {
        name: "description",
        content: "Interactive global map of ARGO ocean floats with filterable metrics.",
      },
      { property: "og:title", content: "SeaBorg Data Explorer" },
      {
        property: "og:description",
        content: "Interactive global map of ARGO ocean floats with filterable metrics.",
      },
    ],
  }),
  component: ExplorerPage,
});

const PAGE = 10;

function ExplorerPage() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  const { data: floats = [], isLoading } = useQuery({
    queryKey: ["floats", 100],
    queryFn: () => getFloats(100),
  });

  const [selectedFloatId, setSelectedFloatId] = useState<string>("all");
  const [page, setPage] = useState(0);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  // Zustand Store
  const explorerFilters = useStore((s) => s.explorerFilters);
  const activeFilterId = useStore((s) => s.activeFilterId);
  const setActiveFilterId = useStore((s) => s.setActiveFilterId);
  const deleteExplorerFilter = useStore((s) => s.deleteExplorerFilter);
  const createExplorerFilter = useStore((s) => s.createExplorerFilter);
  const updateExplorerFilter = useStore((s) => s.updateExplorerFilter);
  const explorerSidebarCollapsed = useStore((s) => s.explorerSidebarCollapsed);
  const toggleExplorerSidebar = useStore((s) => s.toggleExplorerSidebar);

  // Filter Builder state
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);
  const [builderFilterId, setBuilderFilterId] = useState<string | null>(null);
  const [builderName, setBuilderName] = useState("");
  const [builderRules, setBuilderRules] = useState<FilterRule[]>([]);

  const handleEditFilter = (filter: ExplorerFilter, e: React.MouseEvent) => {
    e.stopPropagation();
    setBuilderFilterId(filter.id);
    setBuilderName(filter.name);
    setBuilderRules([...filter.rules]);
    setIsBuilderOpen(true);
  };

  const handleNewFilter = () => {
    setBuilderFilterId(null);
    setBuilderName("");
    setBuilderRules([
      {
        id: "r-" + Math.random().toString(36).substring(7),
        field: "depth",
        operator: "<=",
        value: "200",
      },
    ]);
    setIsBuilderOpen(true);
  };

  const handleSaveFilter = () => {
    if (!builderName.trim()) return;
    const cleanRules = builderRules.filter((r) => String(r.value).trim() !== "");
    if (cleanRules.length === 0) return;

    if (builderFilterId) {
      updateExplorerFilter(builderFilterId, builderName, cleanRules);
    } else {
      createExplorerFilter(builderName, cleanRules);
    }
    setIsBuilderOpen(false);
  };

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: (query) => {
      const data = query.state.data as { status: string } | undefined;
      return data?.status === "ok" ? 30_000 : 3_000;
    },
    staleTime: 0,
  });
  const online = health?.status === "ok";

  const activeFilter = useMemo(() => {
    return explorerFilters.find((f) => f.id === activeFilterId) || null;
  }, [explorerFilters, activeFilterId]);

  // Evaluator engine
  const filtered = useMemo(() => {
    if (!floats) return [];
    let list = floats;
    if (selectedFloatId !== "all") {
      list = list.filter((f) => f.id === selectedFloatId);
    }

    if (activeFilterId === "all" || !activeFilterId) {
      return list;
    }

    const activeFilterObj = explorerFilters.find((f) => f.id === activeFilterId);
    if (!activeFilterObj || !activeFilterObj.rules || activeFilterObj.rules.length === 0) {
      return list;
    }

    return list.filter((float) => {
      return activeFilterObj.rules.every((rule) => {
        const fieldVal = float[rule.field as keyof typeof float];
        if (fieldVal === undefined || fieldVal === null) return false;

        const ruleValStr = String(rule.value).trim();

        if (rule.operator === "contains") {
          return String(fieldVal).toLowerCase().includes(ruleValStr.toLowerCase());
        }

        const floatValNum = Number(fieldVal);
        const ruleValNum = Number(ruleValStr);

        if (isNaN(floatValNum) || isNaN(ruleValNum)) {
          if (rule.operator === "==") return String(fieldVal) === ruleValStr;
          if (rule.operator === "!=") return String(fieldVal) !== ruleValStr;
          return false;
        }

        switch (rule.operator) {
          case "==":
            return floatValNum === ruleValNum;
          case "!=":
            return floatValNum !== ruleValNum;
          case ">":
            return floatValNum > ruleValNum;
          case "<":
            return floatValNum < ruleValNum;
          case ">=":
            return floatValNum >= ruleValNum;
          case "<=":
            return floatValNum <= ruleValNum;
          default:
            return false;
        }
      });
    });
  }, [floats, activeFilterId, explorerFilters, selectedFloatId]);

  // Calculate float counts for each filter in background
  const filterCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    if (!floats) return counts;

    explorerFilters.forEach((filter) => {
      let matchCount = 0;
      floats.forEach((float) => {
        const isMatch = filter.rules.every((rule) => {
          const fieldVal = float[rule.field as keyof typeof float];
          if (fieldVal === undefined || fieldVal === null) return false;

          const ruleValStr = String(rule.value).trim();

          if (rule.operator === "contains") {
            return String(fieldVal).toLowerCase().includes(ruleValStr.toLowerCase());
          }

          const floatValNum = Number(fieldVal);
          const ruleValNum = Number(ruleValStr);

          if (isNaN(floatValNum) || isNaN(ruleValNum)) {
            if (rule.operator === "==") return String(fieldVal) === ruleValStr;
            if (rule.operator === "!=") return String(fieldVal) !== ruleValStr;
            return false;
          }

          switch (rule.operator) {
            case "==":
              return floatValNum === ruleValNum;
            case "!=":
              return floatValNum !== ruleValNum;
            case ">":
              return floatValNum > ruleValNum;
            case "<":
              return floatValNum < ruleValNum;
            case ">=":
              return floatValNum >= ruleValNum;
            case "<=":
              return floatValNum <= ruleValNum;
            default:
              return false;
          }
        });
        if (isMatch) matchCount++;
      });
      counts[filter.id] = matchCount;
    });

    return counts;
  }, [floats, explorerFilters]);

  const totalPages = Math.max(1, Math.ceil((filtered || []).length / PAGE));
  const pageRows = (filtered || []).slice(page * PAGE, page * PAGE + PAGE);

  if (mounted && !online) {
    return (
      <div className="mx-auto w-full max-w-7xl px-6 py-10 lg:px-10 flex flex-col items-center justify-center min-h-[450px]">
        <GlassCard className="p-8 max-w-md w-full text-center flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-500 animate-pulse">
            <Radio className="h-6 w-6" />
          </div>
          <h2 className="text-xl font-semibold text-foreground">
            Waiting for backend connection...
          </h2>
          <p className="text-sm text-muted-foreground">
            Please start the SeaBorg API server. The data explorer and interactive map will load
            automatically once a connection is established.
          </p>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-10 lg:px-10">
      <header className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">
          <GradientText>Data Explorer</GradientText>
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {filtered.length} of {floats.length} floats · live positions, depths, and surface
          temperatures
        </p>
      </header>

      {/* Main Container (Full Width) */}
      <div className="flex flex-col gap-6 w-full">
        {/* Active Filter status row & Float Selector */}
        <div className="flex flex-wrap items-center justify-between gap-4 bg-white/[0.01] border border-[var(--glass-border)] rounded-xl p-3.5 animate-in fade-in duration-200 relative">
          <div className="flex items-center gap-3">
            {/* Hover/Click Filters Dropdown */}
            <div
              className="relative shrink-0"
              onMouseEnter={() => setDropdownOpen(true)}
              onMouseLeave={() => setDropdownOpen(false)}
            >
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-1.5 rounded-lg border border-[var(--glass-border)] bg-card px-3 py-1.5 text-xs font-semibold text-muted-foreground transition-all hover:border-teal/40 hover:text-foreground cursor-pointer shrink-0"
              >
                <Filter className="h-3.5 w-3.5 text-teal" />
                <span>Filter</span>
              </button>

              {/* Floating dropdown panel */}
              <div
                className={cn(
                  "absolute left-0 top-full mt-2 w-[320px] glass rounded-xl border border-[var(--glass-border)] bg-black/95 p-4 shadow-2xl transition-all duration-200 z-50 flex flex-col gap-3",
                  dropdownOpen
                    ? "visible opacity-100 translate-y-0 scale-100 animate-in fade-in zoom-in-95"
                    : "invisible opacity-0 translate-y-1 scale-95",
                )}
              >
                <div className="flex items-center justify-between border-b border-[var(--glass-border)] pb-2.5">
                  <div className="flex items-center gap-2 font-semibold text-xs text-foreground uppercase tracking-wider font-mono">
                    <SlidersHorizontal className="h-3.5 w-3.5 text-teal" />
                    <span>Filter History</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleNewFilter();
                      setDropdownOpen(false);
                    }}
                    className="p-1.5 rounded-lg border border-teal/20 bg-teal/5 text-teal hover:bg-teal/10 transition-colors cursor-pointer"
                    title="Create Custom Filter"
                  >
                    <Plus className="h-3.5 w-3.5" />
                  </button>
                </div>

                {/* Saved Filters List */}
                <div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto pr-1">
                  {/* All Floats Option */}
                  <div
                    onClick={() => {
                      setActiveFilterId("all");
                      setPage(0);
                      setDropdownOpen(false);
                    }}
                    className={cn(
                      "flex cursor-pointer items-center justify-between rounded-lg border p-2.5 text-xs transition-all hover:bg-white/[0.02]",
                      activeFilterId === "all" || !activeFilterId
                        ? "border-teal/40 bg-teal/5 text-foreground font-medium shadow-[0_0_12px_rgba(0,212,170,0.08)]"
                        : "border-[var(--glass-border)] bg-transparent text-muted-foreground hover:text-foreground",
                    )}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <Filter className="h-3.5 w-3.5 text-teal/70" />
                      <span className="truncate">All Floats</span>
                    </div>
                    <span className="rounded-full bg-white/5 border border-white/10 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
                      {floats.length}
                    </span>
                  </div>

                  {/* Filter Items */}
                  {explorerFilters.length === 0 ? (
                    <div className="py-6 text-center text-xs text-muted-foreground">
                      No custom filters. Click "+" to build one!
                    </div>
                  ) : (
                    explorerFilters.map((filter) => {
                      const isActive = activeFilterId === filter.id;
                      const matchCount = filterCounts[filter.id] ?? 0;
                      return (
                        <div
                          key={filter.id}
                          onClick={() => {
                            setActiveFilterId(filter.id);
                            setPage(0);
                            setDropdownOpen(false);
                          }}
                          className={cn(
                            "group/item flex cursor-pointer flex-col gap-1.5 rounded-lg border p-2 text-xs transition-all hover:bg-white/[0.02]",
                            isActive
                              ? "border-teal/40 bg-teal/5 text-foreground font-medium shadow-[0_0_12px_rgba(0,212,170,0.08)]"
                              : "border-[var(--glass-border)] bg-transparent text-muted-foreground hover:text-foreground",
                          )}
                        >
                          <div className="flex items-center justify-between w-full min-w-0">
                            <span className="truncate font-semibold">{filter.name}</span>
                            <div className="flex items-center gap-1.5 shrink-0 ml-2">
                              <span
                                className={cn(
                                  "rounded-full px-1.5 py-0.5 text-[9px] font-mono",
                                  isActive
                                    ? "bg-teal/10 border border-teal/20 text-teal"
                                    : "bg-white/5 border border-white/10 text-muted-foreground",
                                )}
                              >
                                {matchCount}
                              </span>

                              <button
                                onClick={(e) => {
                                  handleEditFilter(filter, e);
                                  setDropdownOpen(false);
                                }}
                                className="opacity-0 group-hover/item:opacity-100 p-0.5 rounded text-muted-foreground hover:text-teal hover:bg-white/[0.06] transition-opacity cursor-pointer"
                                title="Edit filter"
                              >
                                <Edit2 className="h-3 w-3" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (
                                    confirm(
                                      `Are you sure you want to delete the filter "${filter.name}"?`,
                                    )
                                  ) {
                                    deleteExplorerFilter(filter.id);
                                  }
                                }}
                                className="opacity-0 group-hover/item:opacity-100 p-0.5 rounded text-muted-foreground hover:text-red-400 hover:bg-white/[0.06] transition-opacity cursor-pointer"
                                title="Delete filter"
                              >
                                <Trash2 className="h-3 w-3" />
                              </button>
                            </div>
                          </div>

                          {/* Rules preview pills */}
                          <div className="flex flex-wrap gap-1">
                            {filter.rules.map((rule) => (
                              <span
                                key={rule.id}
                                className="rounded bg-white/5 border border-white/5 px-1 py-0.2 text-[9px] font-mono scale-[0.95] origin-left text-muted-foreground/80"
                              >
                                {rule.field} {rule.operator} {rule.value}
                              </span>
                            ))}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>

            {/* Active filter status description */}
            {activeFilter && activeFilterId !== "all" ? (
              <div className="flex items-center gap-2 bg-teal/5 border border-teal/20 px-3 py-1.5 rounded-lg text-xs text-teal animate-in fade-in duration-200">
                <span className="font-semibold">{activeFilter.name}:</span>
                <span className="text-muted-foreground font-mono text-[11px] flex gap-1">
                  {activeFilter.rules.map((r) => `${r.field}${r.operator}${r.value}`).join(" · ")}
                </span>
                <button
                  onClick={() => setActiveFilterId("all")}
                  className="ml-1 p-0.5 rounded text-teal hover:bg-teal/10 transition-colors cursor-pointer"
                  title="Clear filter"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ) : (
              <span className="text-xs text-muted-foreground font-medium py-1.5">
                Showing all floats (no filter applied)
              </span>
            )}
          </div>

          {/* Right side: Float selector dropdown */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground font-medium">Select Float:</span>
            <select
              value={selectedFloatId}
              onChange={(e) => {
                setSelectedFloatId(e.target.value);
                setPage(0);
              }}
              className="rounded-lg border border-[var(--glass-border)] bg-card text-foreground px-3 py-1.5 text-xs outline-none focus:border-teal/40 transition-all duration-200 cursor-pointer shadow-sm hover:border-teal/20"
            >
              <option value="all">All Floats ({floats.length})</option>
              {floats.map((f) => (
                <option key={f.id} value={f.id}>
                  Float {f.id} ({f.temp}°C, {f.depth}m)
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Map */}
        <GlassCard hover={false} className="overflow-hidden p-0">
          <div className="flex items-center justify-between border-b border-[var(--glass-border)] px-5 py-3">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-teal" />
              <h3 className="text-sm font-semibold">Global float positions</h3>
            </div>
            <span className="font-mono text-[11px] text-muted-foreground">
              scattergeo · natural earth
            </span>
          </div>
          <div className="h-[440px] w-full">
            {isLoading ? (
              <Shimmer className="m-4 h-[400px]" />
            ) : (
              <PlotlyChart
                data={[
                  {
                    type: "scattergeo",
                    mode: "markers",
                    lat: filtered.map((f) => f.lat),
                    lon: filtered.map((f) => f.lng),
                    text: filtered.map((f) => `${f.id}<br>${f.temp}°C · ${f.depth}m`),
                    marker: {
                      size: 8,
                      color: filtered.map((f) => f.temp),
                      colorscale: [
                        [0, "#00d4aa"],
                        [1, "#00a8ff"],
                      ],
                      line: { color: "rgba(255,255,255,0.25)", width: 0.5 },
                      colorbar: {
                        title: { text: "°C" },
                        outlinewidth: 0,
                        thickness: 10,
                      },
                    },
                    hovertemplate: "%{text}<extra></extra>",
                  },
                ]}
                layout={{ margin: { l: 0, r: 0, t: 0, b: 0 } }}
              />
            )}
          </div>
        </GlassCard>

        {/* Table */}
        <GlassCard hover={false} className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--glass-border)] text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                  <th className="px-5 py-3 font-medium">Float ID</th>
                  <th className="px-5 py-3 font-medium">Lat</th>
                  <th className="px-5 py-3 font-medium">Lng</th>
                  <th className="px-5 py-3 font-medium">Depth</th>
                  <th className="px-5 py-3 font-medium">Temp</th>
                  <th className="px-5 py-3 font-medium">Salinity</th>
                  <th className="px-5 py-3 font-medium">Last Reading</th>
                </tr>
              </thead>
              <tbody>
                {pageRows.map((f) => (
                  <tr
                    key={f.id}
                    className="border-b border-[var(--glass-border)]/60 transition-colors hover:bg-white/[0.02]"
                  >
                    <td className="px-5 py-3 font-mono text-xs text-teal">{f.id}</td>
                    <td className="px-5 py-3 font-mono text-xs">{f.lat.toFixed(2)}</td>
                    <td className="px-5 py-3 font-mono text-xs">{f.lng.toFixed(2)}</td>
                    <td className="px-5 py-3 font-mono text-xs">{f.depth} m</td>
                    <td className="px-5 py-3 font-mono text-xs">{f.temp}°C</td>
                    <td className="px-5 py-3 font-mono text-xs">{f.salinity}</td>
                    <td className="px-5 py-3 font-mono text-xs text-muted-foreground">
                      {f.last_reading}
                    </td>
                  </tr>
                ))}
                {pageRows.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-5 py-10 text-center text-muted-foreground font-medium"
                    >
                      No floats match the selected criteria. Try adjusting your filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between border-t border-[var(--glass-border)] px-5 py-3 text-xs text-muted-foreground">
            <span className="font-mono">
              Page {page + 1} / {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="grid h-7 w-7 place-items-center rounded-md border border-[var(--glass-border)] bg-white/[0.02] transition-colors hover:text-foreground disabled:opacity-40 cursor-pointer"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="grid h-7 w-7 place-items-center rounded-md border border-[var(--glass-border)] bg-white/[0.02] transition-colors hover:text-foreground disabled:opacity-40 cursor-pointer"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </GlassCard>
      </div>

      {/* Filter Builder Modal */}
      {isBuilderOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <GlassCard
            hover={false}
            className="w-full max-w-lg border border-[var(--glass-border)] bg-card rounded-2xl p-6 shadow-2xl flex flex-col gap-4"
          >
            <div className="flex items-center justify-between border-b border-[var(--glass-border)] pb-3">
              <h3 className="text-sm font-semibold flex items-center gap-2 text-foreground">
                <SlidersHorizontal className="h-4 w-4 text-teal" />
                {builderFilterId ? "Edit Filter" : "Create Custom Filter"}
              </h3>
              <button
                onClick={() => setIsBuilderOpen(false)}
                className="text-muted-foreground hover:text-foreground transition-colors p-1 cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex flex-col gap-4">
              {/* Filter Name */}
              <div>
                <label className="block text-[10px] text-muted-foreground uppercase tracking-wider font-mono mb-1.5">
                  Filter Name
                </label>
                <input
                  type="text"
                  placeholder="e.g., Warm Shallow Water"
                  value={builderName}
                  onChange={(e) => setBuilderName(e.target.value)}
                  className="w-full rounded-lg border border-[var(--glass-border)] bg-background text-foreground px-3 py-2 text-xs outline-none focus:border-teal/40 transition-colors"
                />
              </div>

              {/* Rules Section */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-mono">
                    Criteria (match all)
                  </span>
                  <button
                    onClick={() => {
                      setBuilderRules([
                        ...builderRules,
                        {
                          id: "r-" + Math.random().toString(36).substring(7),
                          field: "depth",
                          operator: "<=",
                          value: "",
                        },
                      ]);
                    }}
                    className="flex items-center gap-1 text-[10.5px] text-teal hover:underline font-semibold cursor-pointer"
                  >
                    <Plus className="h-3 w-3" /> Add Rule
                  </button>
                </div>

                <div className="flex flex-col gap-2 max-h-[220px] overflow-y-auto pr-1">
                  {builderRules.length === 0 ? (
                    <div className="text-center py-4 text-xs text-muted-foreground border border-dashed border-[var(--glass-border)] rounded-lg">
                      No rules added. Click "Add Rule" to add criteria.
                    </div>
                  ) : (
                    builderRules.map((rule, idx) => (
                      <div
                        key={rule.id}
                        className="flex items-center gap-2 bg-white/[0.01] border border-[var(--glass-border)] rounded-lg p-2 animate-in slide-in-from-top-2 duration-150"
                      >
                        {/* Field select */}
                        <select
                          value={rule.field}
                          onChange={(e) => {
                            const val = e.target.value as FilterRule["field"];
                            setBuilderRules(
                              builderRules.map((r, i) => (i === idx ? { ...r, field: val } : r)),
                            );
                          }}
                          className="rounded border border-[var(--glass-border)] bg-background text-foreground text-xs px-2 py-1 outline-none cursor-pointer flex-1"
                        >
                          <option value="depth">Depth (m)</option>
                          <option value="temp">Temp (°C)</option>
                          <option value="salinity">Salinity (PSU)</option>
                          <option value="lat">Latitude</option>
                          <option value="lng">Longitude</option>
                          <option value="id">Float ID</option>
                        </select>

                        {/* Operator select */}
                        <select
                          value={rule.operator}
                          onChange={(e) => {
                            const val = e.target.value as FilterRule["operator"];
                            setBuilderRules(
                              builderRules.map((r, i) => (i === idx ? { ...r, operator: val } : r)),
                            );
                          }}
                          className="rounded border border-[var(--glass-border)] bg-background text-foreground text-xs px-2 py-1 outline-none cursor-pointer w-24 shrink-0"
                        >
                          <option value="==">==</option>
                          <option value="!=">!=</option>
                          <option value=">">&gt;</option>
                          <option value="<">&lt;</option>
                          <option value=">=">&gt;=</option>
                          <option value="<=">&lt;=</option>
                          <option value="contains">contains</option>
                        </select>

                        {/* Value input */}
                        <input
                          type="text"
                          placeholder="value"
                          value={rule.value}
                          onChange={(e) => {
                            const val = e.target.value;
                            setBuilderRules(
                              builderRules.map((r, i) => (i === idx ? { ...r, value: val } : r)),
                            );
                          }}
                          className="rounded border border-[var(--glass-border)] bg-background text-foreground text-xs px-2 py-1 outline-none w-24 shrink-0 focus:border-teal/40"
                        />

                        {/* Delete rule button */}
                        <button
                          onClick={() => {
                            setBuilderRules(builderRules.filter((_, i) => i !== idx));
                          }}
                          className="p-1 rounded text-muted-foreground hover:text-red-400 hover:bg-white/[0.04] transition-colors cursor-pointer"
                          title="Remove rule"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="mt-4 flex justify-end gap-3 border-t border-[var(--glass-border)] pt-4">
              <button
                onClick={() => setIsBuilderOpen(false)}
                className="rounded-lg px-4 py-2 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveFilter}
                disabled={!builderName.trim() || builderRules.length === 0}
                className="flex items-center gap-1.5 rounded-lg bg-teal px-4 py-2 text-xs font-semibold text-black hover:opacity-90 transition-colors disabled:opacity-40 cursor-pointer"
              >
                <Save className="h-3.5 w-3.5" />
                Save Filter
              </button>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
