import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export function GradientText({
  children,
  className,
  as: As = "span",
}: {
  children: ReactNode;
  className?: string;
  as?: "span" | "h1" | "h2" | "h3";
}) {
  return (
    <As
      className={cn("text-gradient", className)}
      style={{
        backgroundSize: "200% 200%",
        animation: "gradient-shift 8s ease infinite",
      }}
    >
      {children}
    </As>
  );
}
