import { Radio } from "lucide-react";
import { GlassCard } from "./GlassCard";

interface ConnectionOverlayProps {
  message?: string;
  description?: string;
}

export function ConnectionOverlay({
  message = "Connecting to SeaBorg Intelligence...",
  description = "Establishing a secure connection to the database. Dashboard and charts will load automatically."
}: ConnectionOverlayProps) {
  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-10 lg:px-10 flex flex-col items-center justify-center min-h-[450px]">
      <GlassCard className="p-8 max-w-md w-full text-center flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-full bg-teal/10 flex items-center justify-center text-teal animate-pulse">
          <Radio className="h-6 w-6 animate-pulse" />
        </div>
        <h2 className="text-xl font-semibold text-foreground tracking-tight">
          {message}
        </h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          {description}
        </p>
      </GlassCard>
    </div>
  );
}
