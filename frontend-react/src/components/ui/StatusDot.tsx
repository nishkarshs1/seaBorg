import { cn } from "@/lib/utils";

type Props = { color?: "green" | "teal" | "amber"; size?: number; className?: string };

const colors: Record<NonNullable<Props["color"]>, string> = {
  green: "#22c55e",
  teal: "#00d4aa",
  amber: "#f59e0b",
};

export function StatusDot({ color = "green", size = 8, className }: Props) {
  return (
    <span
      className={cn("inline-block rounded-full", className)}
      style={{
        width: `${size}px`,
        height: `${size}px`,
        background: colors[color],
        animation: "pulse-dot 2s infinite",
      }}
    />
  );
}
