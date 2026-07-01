import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  FileDown,
  Cog,
  FileText,
  Sparkles,
  Search,
  Bot,
  BarChart3,
  Check,
  X,
  Github,
  FileSearch,
  Radio,
  Waves,
  ArrowDown,
  ArrowUp,
  RotateCw,
  ShieldCheck,
  Filter,
  BookOpen,
  Code2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { GradientText } from "@/components/ui/GradientText";
import { getStats } from "@/lib/api";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "Architecture | SeaBorg" },
      {
        name: "description",
        content:
          "How SeaBorg combines RAG, FAISS, and LLaMA 3 to reason over 694k+ real ARGO float records — inspired by OceanGPT (ACL 2024).",
      },
      { property: "og:title", content: "SeaBorg Architecture" },
      {
        property: "og:description",
        content:
          "RAG-powered ocean intelligence over real ARGO float data. Pipeline, algorithms, and research.",
      },
    ],
  }),
  component: AboutPage,
});

/* ---------- shared section header ---------- */
function SectionHeader({ kicker, title, desc }: { kicker?: string; title: string; desc?: string }) {
  return (
    <div className="mb-6">
      {kicker && (
        <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.22em] text-teal">
          {kicker}
        </div>
      )}
      <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h2>
      {desc && <p className="mt-2 max-w-3xl text-sm text-muted-foreground">{desc}</p>}
    </div>
  );
}

function FadeIn({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/* ---------- data ---------- */
type Step = { n: number; emoji: string; title: string; desc: string; icon: LucideIcon };
const pipeline: Step[] = [
  {
    n: 1,
    emoji: "📁",
    title: "NetCDF Files",
    desc: "Raw ARGO sensor data in .nc format, multidimensional arrays.",
    icon: FileDown,
  },
  {
    n: 2,
    emoji: "🔧",
    title: "ETL Pipeline",
    desc: "xarray parsing → QC filtering → PostgreSQL + Parquet.",
    icon: Cog,
  },
  {
    n: 3,
    emoji: "📝",
    title: "Text Summaries",
    desc: "Each row converted to a natural-language summary.",
    icon: FileText,
  },
  {
    n: 4,
    emoji: "🧠",
    title: "Embeddings",
    desc: "all-MiniLM-L6-v2 → 384-dimensional vectors.",
    icon: Sparkles,
  },
  {
    n: 5,
    emoji: "🔍",
    title: "FAISS Search",
    desc: "Semantic similarity search, retrieves Top-5 records.",
    icon: Search,
  },
  {
    n: 6,
    emoji: "🤖",
    title: "LLaMA 3",
    desc: "Context-grounded generation via Groq API.",
    icon: Bot,
  },
  {
    n: 7,
    emoji: "📊",
    title: "Answer + Chart",
    desc: "Natural-language response + interactive visualization.",
    icon: BarChart3,
  },
];

type Algo = { title: string; subtitle: string; desc: string; color: string };
const algos: Algo[] = [
  {
    title: "Sentence Transformers",
    subtitle: "Model: all-MiniLM-L6-v2",
    desc: "Bi-encoder neural network, 6-layer transformer, 384-D embeddings. Converts ocean data rows into semantic vectors.",
    color: "#00d4aa",
  },
  {
    title: "FAISS",
    subtitle: "Facebook AI Similarity Search",
    desc: "Approximate Nearest Neighbor search using IndexFlatL2 for sub-millisecond search on CPU.",
    color: "#00a8ff",
  },
  {
    title: "RAG Architecture",
    subtitle: "Retrieval-Augmented Generation",
    desc: "Hybrid retriever + generator. The LLM only reads retrieved real sensor data, eliminating hallucinations.",
    color: "#22d3ee",
  },
  {
    title: "LLaMA 3 via Groq",
    subtitle: "llama-3.1-8b-instant",
    desc: "Ultra-fast LPU inference. Factual temperature 0.2, 1024 max tokens.",
    color: "#a78bfa",
  },
  {
    title: "Natural Language → SQL",
    subtitle: "LLM Query Translation",
    desc: "Generates PostgreSQL queries dynamically with safety filters that block SQL injection.",
    color: "#fb923c",
  },
  {
    title: "Quality Control Pipeline",
    subtitle: "Scientific Data Filtering",
    desc: "Accepts only ARGO QC flags 1 & 2. Validates temp −3 °C to 40 °C, salinity 20–42 PSU, depth > 0 m.",
    color: "#34d399",
  },
];

const ragRows: {
  approach: string;
  pros: string;
  cons: string;
  uses: "yes" | "no" | "partial";
  highlight?: boolean;
}[] = [
  {
    approach: "RAG (Retrieval-Augmented)",
    pros: "Always uses latest data, no hallucination, cheap",
    cons: "Slower than direct LLM",
    uses: "yes",
    highlight: true,
  },
  {
    approach: "Fine-tuning",
    pros: "Fast inference, domain adapted",
    cons: "Expensive, goes stale instantly",
    uses: "no",
  },
  {
    approach: "Prompt engineering",
    pros: "Simple, no training needed",
    cons: "Limited context window",
    uses: "partial",
  },
  {
    approach: "Vector DB only",
    pros: "Fast retrieval, good for search",
    cons: "No natural-language generation",
    uses: "no",
  },
];

const diveCycle = [
  { depth: "Surface (0 m)", emoji: "📡", text: "Transmit data via satellite", icon: Radio },
  {
    depth: "Park depth (1000 m)",
    emoji: "🌊",
    text: "Drift with currents for ~9 days",
    icon: Waves,
  },
  {
    depth: "Profile depth (2000 m)",
    emoji: "⬇️",
    text: "Descend to bottom of cycle",
    icon: ArrowDown,
  },
  {
    depth: "Ascent profiling",
    emoji: "⬆️",
    text: "Measure temp / salinity every ~2 m",
    icon: ArrowUp,
  },
  { depth: "Surface (0 m)", emoji: "🔄", text: "Repeat cycle every 10 days", icon: RotateCw },
];

const comparisonRows = [
  { metric: "Primary Method", oceanGpt: "Llama-2 Fine-tuning", seaBorg: "Llama-3 + RAG + FAISS" },
  {
    metric: "Data Grounding",
    oceanGpt: "Synthetic data (DoInstruct)",
    seaBorg: "Real ARGO profiles (694k rows)",
  },
  { metric: "Freshness", oceanGpt: "Static training cutoff", seaBorg: "Real-time index queries" },
  {
    metric: "Verifiability",
    oceanGpt: "Hallucination risk",
    seaBorg: "Cites SQL + retrieved rows",
  },
];

const stack = [
  { name: "Frontend", items: ["React", "Tailwind CSS", "Vite", "Plotly"] },
  { name: "Backend", items: ["FastAPI", "Python 3.11", "Uvicorn"] },
  { name: "AI / ML", items: ["LLaMA 3 (Groq)", "FAISS", "Sentence Transformers"] },
  { name: "Data Engineering", items: ["xarray", "netCDF4", "PostgreSQL", "Pandas"] },
];

type Value = { title: string; desc: string; icon: LucideIcon; color: string };
const coreValues: Value[] = [
  {
    title: "Factual Grounding · Zero-Hallucination AI",
    desc: "Enforces strict RAG. LLaMA 3 is restricted to generate answers using only the top-5 real sensor readings retrieved from our vector index.",
    icon: ShieldCheck,
    color: "#00d4aa",
  },
  {
    title: "Scientific Quality Control First",
    desc: "Incoming NetCDF data is filtered through ARGO QC flags (accepting only Flag 1 & 2). Rejects invalid readings (temp outside −3°C to 40°C, salinity outside 20–42 PSU).",
    icon: Filter,
    color: "#34d399",
  },
  {
    title: "Open Science Accessibility",
    desc: "Translates plain natural-language queries into database lookups, making global ocean profiling accessible to anyone — no SQL, no GIS background required.",
    icon: BookOpen,
    color: "#00a8ff",
  },
  {
    title: "Structured Transparency",
    desc: "Renders the exact SQL query executed against the database in the UI alongside exportable CSV files. Every answer is auditable end-to-end.",
    icon: Code2,
    color: "#a78bfa",
  },
];

/* ---------- page ---------- */
function AboutPage() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: getStats });
  const totalRows = (stats.data?.total_rows ?? 694182).toLocaleString("en-US");
  const floats = stats.data?.unique_floats ?? 43;
  const earliest = (stats.data?.earliest_date ?? "2002-11-11").slice(0, 4);
  const latest = (stats.data?.latest_date ?? "2026-06-08").slice(0, 4);

  const heroMetrics = [
    { label: "ARGO Records", value: totalRows, accent: "#00d4aa" },
    { label: "Embeddings", value: "384D", accent: "#00a8ff" },
    { label: "FAISS Speed", value: "16.85ms", accent: "#22d3ee" },
    { label: "QC Pass Rate", value: "75.34%", accent: "#34d399" },
    { label: "LLM Latency", value: "~1.2s", accent: "#a78bfa" },
  ];

  const perf = [
    { label: "Total ARGO Records", value: totalRows },
    { label: "Active Floats Used", value: String(floats) },
    { label: "Date Coverage", value: `${earliest} – ${latest}` },
    { label: "Max Depth Recorded", value: "2,054 m" },
    { label: "QC Pass Rate", value: "75.34%" },
    { label: "FAISS Retrieval", value: "16.85 ms" },
    { label: "Groq API Latency", value: "~1.2 s" },
    { label: "Avg LLM Tokens", value: "84" },
    { label: "LLM Temperature", value: "0.2" },
    { label: "Active LLM", value: "llama-3.1-8b" },
    { label: "Embedding Dim", value: "384D" },
    { label: "Embedding Model", value: "MiniLM-L6-v2" },
  ];

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12 lg:px-10">
      {/* SECTION 1 — Hero */}
      <FadeIn>
        <header className="mb-10 text-center">
          <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">
            <GradientText>SeaBorg</GradientText>
          </h1>
          <p className="mt-3 text-base text-muted-foreground sm:text-lg">
            Ocean Intelligence Platform
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            <span
              className="rounded-full border px-3 py-1 text-xs"
              style={{
                borderColor: "rgba(0,212,170,0.35)",
                background: "rgba(0,212,170,0.08)",
                color: "#00d4aa",
              }}
            >
              🎓 Based on OceanGPT · ACL 2024
            </span>
            <span
              className="rounded-full border px-3 py-1 text-xs"
              style={{
                borderColor: "rgba(0,168,255,0.35)",
                background: "rgba(0,168,255,0.08)",
                color: "#00a8ff",
              }}
            >
              🌊 Real ARGO Float Data
            </span>
          </div>
        </header>
      </FadeIn>

      <FadeIn delay={0.05}>
        <div className="mb-16 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {heroMetrics.map((m) => (
            <div key={m.label} className="glass relative overflow-hidden px-4 py-5 text-center">
              <div
                className="absolute inset-x-0 top-0 h-px"
                style={{
                  background: `linear-gradient(90deg, transparent, ${m.accent}, transparent)`,
                }}
              />
              <div
                className="font-mono text-2xl font-semibold tabular-nums sm:text-[28px]"
                style={{ color: m.accent }}
              >
                {m.value}
              </div>
              <div className="mt-1 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                {m.label}
              </div>
            </div>
          ))}
        </div>
      </FadeIn>

      {/* SECTION · Core Values */}
      <section className="mb-20">
        <FadeIn>
          <SectionHeader
            kicker="00 · Mission"
            title="Core Values"
            desc="The principles that shape every retrieval, every prompt, and every answer SeaBorg returns."
          />
        </FadeIn>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {coreValues.map((v, i) => {
            const Icon = v.icon;
            return (
              <FadeIn key={v.title} delay={i * 0.05}>
                <GlassCard
                  className="relative h-full overflow-hidden"
                  style={{ borderLeft: `2px solid ${v.color}` }}
                >
                  <div className="flex items-start gap-4">
                    <span
                      className="grid h-11 w-11 shrink-0 place-items-center rounded-xl"
                      style={{
                        background: `${v.color}14`,
                        border: `1px solid ${v.color}44`,
                        color: v.color,
                      }}
                    >
                      <Icon className="h-5 w-5" />
                    </span>
                    <div>
                      <h3 className="text-base font-semibold leading-snug">{v.title}</h3>
                      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{v.desc}</p>
                    </div>
                  </div>
                </GlassCard>
              </FadeIn>
            );
          })}
        </div>
      </section>

      {/* SECTION 2 — Pipeline */}
      <section className="mb-20">
        <FadeIn>
          <SectionHeader
            kicker="01 · End-to-end"
            title="The SeaBorg Pipeline"
            desc="Raw NetCDF on one end, a cited natural-language answer on the other. Seven stages, fully observable."
          />
        </FadeIn>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
          {pipeline.map((s, i) => {
            const Icon = s.icon;
            return (
              <FadeIn key={s.n} delay={i * 0.05}>
                <GlassCard className="relative flex h-full flex-col">
                  <div className="mb-3 flex items-center justify-between">
                    <span
                      className="grid h-10 w-10 place-items-center rounded-lg text-base"
                      style={{
                        background:
                          "linear-gradient(135deg, rgba(0,212,170,0.18), rgba(0,168,255,0.18))",
                        border: "1px solid rgba(0,212,170,0.3)",
                        color: "#00d4aa",
                      }}
                    >
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      Step {s.n}
                    </span>
                  </div>
                  <div className="text-lg">{s.emoji}</div>
                  <h3 className="mt-1 text-sm font-semibold">{s.title}</h3>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{s.desc}</p>
                </GlassCard>
              </FadeIn>
            );
          })}
        </div>
      </section>

      {/* SECTION 3 — ML Algorithms */}
      <section className="mb-20">
        <FadeIn>
          <SectionHeader
            kicker="02 · Under the hood"
            title="ML Algorithms & Techniques"
            desc="Every component is an off-the-shelf, well-understood building block — no exotic dependencies."
          />
        </FadeIn>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {algos.map((a, i) => (
            <FadeIn key={a.title} delay={i * 0.04}>
              <GlassCard
                className="relative h-full overflow-hidden"
                style={{ borderTop: `2px solid ${a.color}` }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-base font-semibold">{a.title}</h3>
                    <div className="mt-0.5 font-mono text-[11px]" style={{ color: a.color }}>
                      {a.subtitle}
                    </div>
                  </div>
                  <span
                    className="shrink-0 rounded-full border px-2 py-0.5 text-[10px]"
                    style={{
                      borderColor: `${a.color}55`,
                      background: `${a.color}14`,
                      color: a.color,
                    }}
                  >
                    Used in SeaBorg ✅
                  </span>
                </div>
                <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{a.desc}</p>
              </GlassCard>
            </FadeIn>
          ))}
        </div>
      </section>

      {/* SECTION 4 — System performance */}
      <section className="mb-20">
        <FadeIn>
          <SectionHeader
            kicker="03 · Live numbers"
            title="System Performance"
            desc="Snapshot of the running system, measured end-to-end."
          />
        </FadeIn>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {perf.map((p, i) => (
            <FadeIn key={p.label} delay={i * 0.03}>
              <div className="glass px-5 py-5">
                <div className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                  {p.label}
                </div>
                <div className="mt-2 font-mono text-xl font-semibold text-foreground tabular-nums">
                  {p.value}
                </div>
              </div>
            </FadeIn>
          ))}
        </div>
      </section>

      {/* SECTION 5 — Why RAG */}
      <section className="mb-20">
        <FadeIn>
          <SectionHeader
            kicker="04 · Architecture choice"
            title="Why RAG?"
            desc="Four common approaches, compared on the dimensions that actually matter for ocean data."
          />
        </FadeIn>
        <FadeIn delay={0.05}>
          <GlassCard hover={false} className="overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--glass-border)] text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                    <th className="px-5 py-3 font-medium">Approach</th>
                    <th className="px-5 py-3 font-medium">Pros</th>
                    <th className="px-5 py-3 font-medium">Cons</th>
                    <th className="px-5 py-3 font-medium">SeaBorg Uses?</th>
                  </tr>
                </thead>
                <tbody>
                  {ragRows.map((r) => (
                    <tr
                      key={r.approach}
                      className="border-b border-[var(--glass-border)]/60 transition-colors hover:bg-white/[0.02]"
                      style={
                        r.highlight
                          ? {
                              background:
                                "linear-gradient(90deg, rgba(0,212,170,0.08), rgba(0,168,255,0.04))",
                              boxShadow:
                                "inset 0 0 0 1px rgba(0,212,170,0.35), 0 0 24px -8px rgba(0,212,170,0.45)",
                            }
                          : undefined
                      }
                    >
                      <td className="px-5 py-3 font-medium">{r.approach}</td>
                      <td className="px-5 py-3 text-muted-foreground">{r.pros}</td>
                      <td className="px-5 py-3 text-muted-foreground">{r.cons}</td>
                      <td className="px-5 py-3">
                        {r.uses === "yes" && (
                          <span className="inline-flex items-center gap-1.5 text-teal">
                            <Check className="h-3.5 w-3.5" /> Yes
                          </span>
                        )}
                        {r.uses === "no" && (
                          <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                            <X className="h-3.5 w-3.5" /> No
                          </span>
                        )}
                        {r.uses === "partial" && (
                          <span className="inline-flex items-center gap-1.5 text-ocean">
                            <Check className="h-3.5 w-3.5" /> Partial
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </FadeIn>
        <FadeIn delay={0.1}>
          <div
            className="mt-4 rounded-xl border px-5 py-4 text-sm leading-relaxed text-muted-foreground"
            style={{
              borderColor: "rgba(0,212,170,0.25)",
              background: "linear-gradient(90deg, rgba(0,212,170,0.06), rgba(0,168,255,0.04))",
            }}
          >
            <span className="font-semibold text-foreground">SeaBorg uses RAG</span> because ocean
            data changes constantly. A fine-tuned model would go stale instantly. RAG always
            retrieves the exact, latest ARGO readings dynamically before answering.
          </div>
        </FadeIn>
      </section>

      {/* SECTION 6 — ARGO + Dive Cycle */}
      <section className="mb-20">
        <FadeIn>
          <SectionHeader
            kicker="05 · The instrument"
            title="What are ARGO Floats?"
            desc="The autonomous robotic backbone of modern oceanography."
          />
        </FadeIn>
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <FadeIn>
            <GlassCard className="h-full">
              <div className="text-2xl">🌊</div>
              <h3 className="mt-2 text-lg font-semibold">Autonomous Profilers</h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                ARGO floats are autonomous robotic profilers that drift with ocean currents,
                measuring <span className="text-foreground">Temperature</span>,{" "}
                <span className="text-foreground">Salinity</span>, and{" "}
                <span className="text-foreground">Pressure</span> from the surface down to 2000 m.
                Over <span className="text-teal font-semibold">4,000+</span> floats are active
                globally, forming a real-time climate observation network.
              </p>
              <ul className="mt-4 space-y-2 text-xs text-muted-foreground">
                <li>• Battery-powered, ~4-year operational life</li>
                <li>• Iridium satellite uplink at every surface</li>
                <li>• Data is open and freely redistributed by GDACs</li>
              </ul>
            </GlassCard>
          </FadeIn>

          <FadeIn delay={0.05}>
            <GlassCard className="h-full">
              <div className="text-2xl">🔁</div>
              <h3 className="mt-2 text-lg font-semibold">The 10-Day Dive Cycle</h3>
              <ol className="relative mt-5 space-y-5 border-l border-[var(--glass-border)] pl-6">
                {diveCycle.map((d, i) => {
                  const Icon = d.icon;
                  return (
                    <li key={i} className="relative">
                      <span
                        className="absolute -left-[31px] grid h-6 w-6 place-items-center rounded-full"
                        style={{
                          background:
                            "linear-gradient(135deg, rgba(0,212,170,0.25), rgba(0,168,255,0.25))",
                          border: "1px solid rgba(0,212,170,0.45)",
                          color: "#00d4aa",
                        }}
                      >
                        <Icon className="h-3 w-3" />
                      </span>
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <span>{d.emoji}</span>
                        <span>{d.depth}</span>
                      </div>
                      <div className="text-xs text-muted-foreground">{d.text}</div>
                    </li>
                  );
                })}
              </ol>
            </GlassCard>
          </FadeIn>
        </div>
      </section>

      {/* SECTION 7 — Research */}
      <section className="mb-20">
        <FadeIn>
          <SectionHeader
            kicker="06 · Research lineage"
            title="SeaBorg vs OceanGPT"
            desc="SeaBorg's intelligence is inspired by OceanGPT (ACL 2024) — the first LLM purpose-built for ocean science. Where OceanGPT focused on synthetic data generation and fine-tuning, SeaBorg implements that vision as a live RAG system mapped to real ARGO float readings."
          />
        </FadeIn>
        <FadeIn>
          <GlassCard className="overflow-hidden p-0" hover={false}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--glass-border)] text-left text-[11px] uppercase tracking-wider text-muted-foreground bg-white/[0.02]">
                    <th className="px-5 py-3 font-semibold">Aspect</th>
                    <th className="px-5 py-3 font-semibold text-[#a78bfa]">OceanGPT (ACL 2024)</th>
                    <th className="px-5 py-3 font-semibold text-teal">SeaBorg (RAG)</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonRows.map((r, idx) => (
                    <tr
                      key={r.metric}
                      className={`border-b border-[var(--glass-border)]/60 transition-colors hover:bg-white/[0.01] ${
                        idx === comparisonRows.length - 1 ? "border-none" : ""
                      }`}
                    >
                      <td className="px-5 py-3 font-mono text-[11px] text-muted-foreground">
                        {r.metric}
                      </td>
                      <td className="px-5 py-3 text-xs text-foreground/80">{r.oceanGpt}</td>
                      <td className="px-5 py-3 text-xs font-medium text-foreground">{r.seaBorg}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </FadeIn>

        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          <FadeIn>
            <a
              href="https://github.com/OceanGPT/OceanGPT"
              target="_blank"
              rel="noreferrer"
              className="glass group flex items-center justify-between gap-4 px-5 py-4 transition-colors hover:bg-white/[0.05]"
            >
              <div className="flex items-center gap-3">
                <span
                  className="grid h-10 w-10 place-items-center rounded-lg"
                  style={{
                    background: "rgba(167,139,250,0.12)",
                    border: "1px solid rgba(167,139,250,0.3)",
                    color: "#a78bfa",
                  }}
                >
                  <Github className="h-4 w-4" />
                </span>
                <div>
                  <div className="text-sm font-semibold">🐙 OceanGPT Official Repo</div>
                  <div className="font-mono text-xs text-muted-foreground">
                    github.com/OceanGPT/OceanGPT
                  </div>
                </div>
              </div>
              <span className="text-xs text-teal opacity-0 transition-opacity group-hover:opacity-100">
                View on GitHub →
              </span>
            </a>
          </FadeIn>
          <FadeIn delay={0.05}>
            <a
              href="https://arxiv.org/abs/2310.02031"
              target="_blank"
              rel="noreferrer"
              className="glass group flex items-center justify-between gap-4 px-5 py-4 transition-colors hover:bg-white/[0.05]"
            >
              <div className="flex items-center gap-3">
                <span
                  className="grid h-10 w-10 place-items-center rounded-lg"
                  style={{
                    background: "rgba(0,168,255,0.12)",
                    border: "1px solid rgba(0,168,255,0.3)",
                    color: "#00a8ff",
                  }}
                >
                  <FileSearch className="h-4 w-4" />
                </span>
                <div>
                  <div className="text-sm font-semibold">📄 OceanGPT Paper</div>
                  <div className="font-mono text-xs text-muted-foreground">
                    arxiv.org/abs/2310.02031 · Bi et al., ACL 2024
                  </div>
                </div>
              </div>
              <span className="text-xs text-ocean opacity-0 transition-opacity group-hover:opacity-100">
                Read Paper →
              </span>
            </a>
          </FadeIn>
        </div>
      </section>

      {/* SECTION 8 — Tech Stack */}
      <section className="mb-10">
        <FadeIn>
          <SectionHeader
            kicker="07 · Built with"
            title="Tech Stack"
            desc="A pragmatic, fully open-source stack — every layer is swappable."
          />
        </FadeIn>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stack.map((s, i) => (
            <FadeIn key={s.name} delay={i * 0.04}>
              <GlassCard className="h-full">
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-teal">
                  {s.name}
                </div>
                <ul className="mt-3 space-y-1.5 text-sm">
                  {s.items.map((it) => (
                    <li key={it} className="flex items-center gap-2 text-muted-foreground">
                      <span className="h-1 w-1 rounded-full bg-teal" />
                      <span className="text-foreground/90">{it}</span>
                    </li>
                  ))}
                </ul>
              </GlassCard>
            </FadeIn>
          ))}
        </div>
      </section>
    </div>
  );
}
