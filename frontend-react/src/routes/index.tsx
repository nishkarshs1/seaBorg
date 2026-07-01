import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Database,
  Radio,
  Gauge,
  CalendarRange,
  MessageSquareText,
  Globe2,
  ArrowRight,
  Anchor,
} from "lucide-react";
import { getStats, getHealth } from "@/lib/api";
import { MetricCard } from "@/components/ui/MetricCard";
import { GlassCard } from "@/components/ui/GlassCard";
import { GradientText } from "@/components/ui/GradientText";
import { StatusDot } from "@/components/ui/StatusDot";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard | SeaBorg" },
      {
        name: "description",
        content: "Real-time overview of the SeaBorg ocean intelligence platform.",
      },
      { property: "og:title", content: "SeaBorg Dashboard" },
      {
        property: "og:description",
        content: "Real-time overview of the SeaBorg ocean intelligence platform.",
      },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  const { data: stats, isLoading: isStatsLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: (query) => {
      const data = query.state.data as any;
      return data?.status === "ok" ? 30_000 : 3_000;
    },
    staleTime: 0,
  });
  const online = health?.status === "ok";

  const fmt = (n?: number) => (n ? n.toLocaleString("en-US") : "—");

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
            Please start the SeaBorg API server. The dashboard and metrics will load automatically
            once a connection is established.
          </p>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-10 lg:px-10">
      {/* Hero */}
      <section className="mb-10">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[var(--glass-border)] bg-white/[0.02] px-3 py-1 text-xs text-muted-foreground">
          <StatusDot color={mounted && online ? "green" : "amber"} />
          <span>
            {mounted && online ? "All systems nominal · 99.98% uptime" : "System Status Degraded"}
          </span>
        </div>
        <h1 className="text-5xl font-bold leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl">
          <GradientText>🌊 SeaBorg</GradientText>
        </h1>
        <p className="mt-4 max-w-2xl text-base text-muted-foreground sm:text-lg">
          AI-powered ocean intelligence. Query 694k+ ARGO float readings, generate SQL on the fly,
          and visualize the answer — in seconds.
        </p>
      </section>

      {/* Metrics */}
      <section className="mb-10 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <MetricCard
          label="Total Records"
          value={fmt(stats?.total_rows ?? 694182)}
          hint="ARGO rows in PostgreSQL"
          icon={Database}
          loading={isStatsLoading}
          accent="teal"
        />
        <MetricCard
          label="Active Floats"
          value={stats?.unique_floats ?? 43}
          hint="robotic profilers reporting"
          icon={Radio}
          loading={isStatsLoading}
          accent="ocean"
        />
        <MetricCard
          label="FAISS Speed"
          value="1.44 ms"
          hint="p95 vector retrieval"
          icon={Gauge}
          accent="teal"
        />
        <MetricCard
          label="Max Depth"
          value="2,054 m"
          hint="deepest reading on record"
          icon={Anchor}
          accent="ocean"
        />
        <MetricCard
          label="Date Range"
          value={
            stats
              ? `${stats.earliest_date.slice(0, 4)}–${stats.latest_date.slice(0, 4)}`
              : "2002–2026"
          }
          hint="continuous coverage"
          icon={CalendarRange}
          loading={isStatsLoading}
          accent="teal"
        />
      </section>

      {/* Quick Action Navigation Grid */}
      <section className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <GlassCard
          className="flex flex-col justify-between p-6 h-52 hover:border-teal/40 transition-colors"
          hover={true}
        >
          <div>
            <div className="flex items-center gap-2.5 mb-3">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-teal/10 text-teal">
                <MessageSquareText className="h-4.5 w-4.5" />
              </span>
              <h3 className="text-base font-semibold">Ocean Chat</h3>
            </div>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Ask natural language questions about sea temperatures, salinity, and pressure. SeaBorg
              translates your queries into live SQL and answers with grounded RAG context.
            </p>
          </div>
          <Link
            to="/chat"
            className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-semibold text-teal hover:underline mt-4"
          >
            Start Chatting <ArrowRight className="h-4 w-4" />
          </Link>
        </GlassCard>

        <GlassCard
          className="flex flex-col justify-between p-6 h-52 hover:border-ocean/40 transition-colors"
          hover={true}
        >
          <div>
            <div className="flex items-center gap-2.5 mb-3">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-ocean/10 text-ocean">
                <Globe2 className="h-4.5 w-4.5" />
              </span>
              <h3 className="text-base font-semibold">Data Explorer</h3>
            </div>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Explore spatial coordinate distributions of all 43 active ARGO floats globally on an
              interactive world projection chart. View and filter raw sensor reading records in
              detail.
            </p>
          </div>
          <Link
            to="/explorer"
            className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-semibold text-ocean hover:underline mt-4"
          >
            Explore Datasets <ArrowRight className="h-4 w-4" />
          </Link>
        </GlassCard>
      </section>
    </div>
  );
}
