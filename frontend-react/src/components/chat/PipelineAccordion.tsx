import { useState } from "react";
import { ChevronRight, Cpu, AlertTriangle, FileCode, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { AnimatePresence, motion } from "framer-motion";

interface PipelineAccordionProps {
  trace?: string[];
  warnings?: string[];
  sourceFiles?: string[];
}

export function PipelineAccordion({ trace, warnings, sourceFiles }: PipelineAccordionProps) {
  const [open, setOpen] = useState(false);
  const hasTrace = trace && trace.length > 0;
  const hasWarnings = warnings && warnings.length > 0;
  const hasFiles = sourceFiles && sourceFiles.length > 0;

  if (!hasTrace && !hasWarnings && !hasFiles) {
    return null;
  }

  return (
    <div className="group/pipe mt-2 overflow-hidden rounded-lg border border-[var(--glass-border)] bg-secondary/30">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <ChevronRight className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-90")} />
        <Cpu className="h-3.5 w-3.5 text-ocean" />
        <span className="font-medium">Pipeline Info & Trace</span>
        {hasWarnings && (
          <span className="ml-auto flex items-center gap-1 rounded bg-amber-500/10 px-1.5 py-0.5 text-[9px] font-semibold text-amber-500">
            <AlertTriangle className="h-2.5 w-2.5" />
            {warnings.length} warning{warnings.length > 1 ? "s" : ""}
          </span>
        )}
      </button>
      
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="border-t border-[var(--glass-border)] bg-black/10 px-3 py-3"
          >
            {/* 1. EXECUTION TRACE */}
            {hasTrace && (
              <div className="mb-3">
                <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground/80 font-semibold">
                  Execution Trace
                </div>
                <div className="relative border-l border-teal/20 pl-4 ml-1.5 space-y-2">
                  {trace.map((step, i) => (
                    <div key={i} className="relative text-[11px] text-foreground/90 font-mono">
                      <div className="absolute -left-[20.5px] top-[4px] h-2.5 w-2.5 rounded-full border border-teal/40 bg-[#0a0c16] flex items-center justify-center">
                        <div className="h-1 w-1 rounded-full bg-teal" />
                      </div>
                      {step}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 2. VALIDATION WARNINGS */}
            {hasWarnings && (
              <div className="mb-3 rounded border border-amber-500/20 bg-amber-500/5 p-2">
                <div className="mb-1.5 flex items-center gap-1 text-[10px] uppercase tracking-wider font-semibold text-amber-500">
                  <AlertTriangle className="h-3 w-3" />
                  Scientific Boundary Flags
                </div>
                <ul className="list-inside list-disc space-y-1 text-[11px] font-mono text-amber-500/90">
                  {warnings.map((w, i) => (
                    <li key={i} className="leading-relaxed">{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* 3. NETCDF SOURCE FILES */}
            {hasFiles && (
              <div>
                <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground/80 font-semibold">
                  Source NetCDF Datasets
                </div>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {sourceFiles.map((file, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1 rounded border border-[var(--glass-border)] bg-secondary/50 px-2 py-0.5 font-mono text-[10px] text-foreground/90"
                    >
                      <FileCode className="h-3 w-3 text-teal" />
                      {file}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
