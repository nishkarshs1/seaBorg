import type { LucideIcon } from "lucide-react";
import { GlassCard } from "./GlassCard";
import { Shimmer } from "./Shimmer";

type Props = {
  label: string;
  value?: string | number;
  hint?: string;
  icon?: LucideIcon;
  loading?: boolean;
  accent?: "teal" | "ocean";
};

export function MetricCard({ label, value, hint, icon: Icon, loading, accent = "teal" }: Props) {
  const accentColor = accent === "teal" ? "#00d4aa" : "#00a8ff";
  return (
    <GlassCard className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full opacity-30 blur-3xl"
        style={{ background: accentColor }}
      />
      <div className="flex items-start justify-between gap-3">
        <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">{label}</span>
        {Icon && (
          <span
            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg"
            style={{ background: `${accentColor}1a`, color: accentColor }}
          >
            <Icon className="h-4 w-4" />
          </span>
        )}
      </div>
      <div className="mt-4">
        {loading ? (
          <Shimmer className="h-8 w-32" />
        ) : (
          <div className="font-mono text-3xl font-semibold tracking-tight text-foreground">
            {value}
          </div>
        )}
      </div>
      {hint && <div className="mt-1.5 text-xs text-muted-foreground">{hint}</div>}
    </GlassCard>
  );
}
