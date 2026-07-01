import { useState } from "react";
import { ChevronRight, Code2, Copy, Check } from "lucide-react";
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter";
import sql from "react-syntax-highlighter/dist/esm/languages/prism/sql";
import { atomDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { cn } from "@/lib/utils";
import { AnimatePresence, motion } from "framer-motion";
import { useStore } from "@/store";

SyntaxHighlighter.registerLanguage("sql", sql);

export function SqlAccordion({ sqlText }: { sqlText: string }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const theme = useStore((s) => s.theme);
  const isLight = theme === "light";

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(sqlText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* noop */
    }
  };

  return (
    <div className="group/sql mt-3 overflow-hidden rounded-lg border border-[var(--glass-border)] bg-secondary/50">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <ChevronRight className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-90")} />
        <Code2 className="h-3.5 w-3.5 text-teal" />
        <span className="font-medium">View generated SQL</span>
        <span className="ml-auto font-mono text-[10px] uppercase tracking-wider text-muted-foreground/70">
          postgres
        </span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className={cn(
              "relative border-t border-[var(--glass-border)] overflow-hidden transition-colors duration-200",
              isLight ? "bg-[#f0f0f8]" : "bg-transparent",
            )}
          >
            <button
              onClick={copy}
              className="absolute right-2 top-2 z-10 flex items-center gap-1 rounded-md border border-[var(--glass-border)] bg-card/85 backdrop-blur-sm px-2 py-1 text-[10px] text-muted-foreground transition-all duration-200 opacity-0 group-hover/sql:opacity-100 focus-within:opacity-100 hover:text-foreground hover:bg-secondary"
            >
              {copied ? <Check className="h-3 w-3 text-teal" /> : <Copy className="h-3 w-3" />}
              {copied ? "Copied" : "Copy"}
            </button>
            <SyntaxHighlighter
              language="sql"
              style={atomDark}
              className="sql-code-block"
              customStyle={{
                margin: 0,
                padding: "14px 60px 14px 16px",
                background: "transparent",
                fontSize: "12px",
                fontFamily: "JetBrains Mono, monospace",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                overflowWrap: "break-word",
                overflowX: "hidden",
                overflowY: "auto",
                maxWidth: "100%",
              }}
              codeTagProps={{
                style: {
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  overflowWrap: "break-word",
                  fontFamily: "inherit",
                  fontSize: "inherit",
                },
              }}
            >
              {sqlText}
            </SyntaxHighlighter>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
