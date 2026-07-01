import { cn } from "@/lib/utils";

export function Shimmer({ className }: { className?: string }) {
  return (
    <div
      className={cn("rounded-md overflow-hidden", className)}
      style={{
        background:
          "linear-gradient(90deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.10) 50%, rgba(255,255,255,0.04) 100%)",
        backgroundSize: "800px 100%",
        animation: "shimmer 1.6s linear infinite",
      }}
    />
  );
}
